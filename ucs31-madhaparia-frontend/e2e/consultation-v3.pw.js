// Real UI/API journeys against an isolated migrated/seeded V3 audit database.
// Disease presentation requires a backend selection decision; these are software, not clinical, checks.
import { expect, test } from '@playwright/test'

const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000'

test.beforeEach(async ({ page, request }, testInfo) => {
  const email = `consult-${Date.now()}-${testInfo.testId.slice(-6)}@example.com`
  const password = 'Audit-test-only-2026!'
  const registered = await request.post(`${apiURL}/auth/register`, { data: { email, password } })
  expect(registered.ok(), await registered.text()).toBe(true)
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
})

async function mapInput(page, text) {
  await page.goto('/symptoms')
  await page.getByLabel('Symptom description').fill(text)
  const mapped = page.waitForResponse((response) => response.url().endsWith('/nlp/map'))
  await page.getByRole('button', { name: 'Analyse symptoms', exact: true }).click()
  const response = await mapped
  expect(response.ok(), await response.text()).toBe(true)
  return response.json()
}

async function begin(page) {
  await page.getByRole('link', { name: 'Continue to confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm selected symptoms' }).click()
  await page.getByRole('link', { name: 'Continue to prediction' }).click()
  await page.getByLabel('Age', { exact: true }).fill('21')
  await page.getByLabel('Sex', { exact: true }).selectOption('M')
  const next = page.waitForResponse((response) => response.url().endsWith('/predict'))
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  const response = await next
  expect(response.ok(), await response.text()).toBe(true)
  return response.json()
}

async function answerQuestions(page, result, preferUnknown = false) {
  const asked = []
  while (result.status === 'needs_follow_up') {
    const question = result.follow_up_question
    expect(asked).not.toContain(question.id)
    asked.push(question.id)
    expect(asked.length).toBeLessThanOrEqual(5)
    await expect(page.getByRole('heading', { name: question.text, exact: true })).toBeVisible()
    if (asked.length === 1) {
      await page.reload()
      await expect(page.getByRole('heading', { name: question.text, exact: true })).toBeVisible()
    }
    const option = (preferUnknown && !/breath/.test(question.id) &&
      question.options.find((item) => item.value === 'unknown')) ||
      question.options.find((item) => item.value === 'under_3_days') ||
      question.options.find((item) => item.value === 'no') ||
      question.options.find((item) => item.value === 'unknown')
    expect(option, `Question ${question.id} needs an explicit test answer`).toBeTruthy()
    await page.getByRole('radio', { name: option.label, exact: true }).check()
    const next = page.waitForResponse((response) => response.url().endsWith('/predict'))
    await page.getByRole('button', { name: 'Continue / Endelea' }).click()
    const response = await next
    expect(response.ok(), await response.text()).toBe(true)
    result = await response.json()
  }
  return { result, asked }
}

const scenarios = [
  { name: 'informative coughing fits', text: 'I have intense coughing fits and vomiting after coughing for 5 days.', language: 'en', requiresPrimary: true },
  { name: 'English cough and fever', text: 'I have a cough and fever.', language: 'en', fever: 'present' },
  { name: 'Swahili cough and fever', text: 'Nina homa na kikohozi.', language: 'sw', fever: 'present' },
  { name: 'English negation', text: 'I have a cough, but I do not have a fever.', language: 'en', fever: 'absent' },
  { name: 'Swahili negation', text: 'Nina kikohozi lakini sina homa.', language: 'sw', fever: 'absent' },
  { name: 'cough alone', text: 'I have a cough.', language: 'en', fever: null },
  { name: 'fever alone', text: 'I have fever.', language: 'en', fever: 'present' },
  { name: 'headache and tiredness', text: 'I have a headache and feel tired.', language: 'en' },
  { name: 'fever cough sore throat body aches', text: 'I have fever, a cough, a sore throat and body aches.', language: 'en', fever: 'present' },
]

for (const scenario of scenarios) {
  test(`single-primary policy: ${scenario.name}`, async ({ page, request }, testInfo) => {
    await mapInput(page, scenario.text)
    const { result, asked } = await answerQuestions(page, await begin(page), scenario.requiresPrimary)
    expect(['prediction_complete', 'assessment_uncertain', 'insufficient_evidence']).toContain(result.status)
    expect(result.decision.policy_version).toBeTruthy()
    expect(result.predictions.length).toBeLessThanOrEqual(1)
    if (scenario.requiresPrimary) expect(result.primary_prediction).toBeTruthy()
    expect(result.assessment_context.language).toBe(scenario.language)
    if (scenario.fever === null) {
      const feverAnswer = result.follow_up_answers.find((answer) => answer.question_id === 'fever')
      expect(result.assessment_context.symptom_states.fever).toBe(feverAnswer?.answer === 'no' ? 'absent' : undefined)
    } else if (scenario.fever) {
      expect(result.assessment_context.symptom_states.fever).toBe(scenario.fever)
    }
    expect(result.follow_up_answers).toHaveLength(asked.length)
    expect(result.next_steps.length).toBeGreaterThan(0)
    if (result.primary_prediction) {
      expect(result.decision.status).toBe('possible_explanation')
      expect(result.predictions).toEqual([result.primary_prediction])
      await expect(page.getByRole('heading', { name: result.primary_prediction.display_name, exact: true })).toBeVisible()
      await expect(page.locator('.consultation-candidate')).toHaveCount(1)
    } else {
      expect(result.predictions).toEqual([])
      expect(result.decision.status).not.toBe('possible_explanation')
      await expect(page.getByRole('heading', {
        name: scenario.language === 'sw' ? 'Tunahitaji maelezo zaidi' : 'More information is needed', exact: true,
      })).toBeVisible()
      await expect(page.locator('.consultation-candidate')).toHaveCount(0)
    }
    await expect(page.getByText(result.assessment_summary, { exact: true })).toBeVisible()
    expect(await page.locator('.pred34-results').textContent()).not.toMatch(/\d+(?:\.\d+)?%/)
    expect(JSON.stringify(result)).not.toMatch(/model_confidence_percent|raw_relative_score/)
    if (['informative coughing fits', 'English cough and fever', 'headache and tiredness', 'fever cough sore throat body aches'].includes(scenario.name)) {
      const slug = scenario.name.toLowerCase().replaceAll(' ', '-')
      await page.screenshot({ path: `../audit-artifacts/kenya-patient-ui/after-${slug}-desktop.png`, fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      await page.screenshot({ path: `../audit-artifacts/kenya-patient-ui/after-${slug}-mobile.png`, fullPage: true })
    }
    await testInfo.attach('actual-patient-response', { body: JSON.stringify(result, null, 2), contentType: 'application/json' })
    const token = await page.evaluate(() => sessionStorage.getItem('respiracare_access_token'))
    const history = await request.get(`${apiURL}/history/${result.prediction_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(history.ok(), await history.text()).toBe(true)
    const saved = await history.json()
    expect(saved.primary_prediction).toEqual(result.primary_prediction)
    expect(saved.predictions).toEqual(result.predictions)
    await page.goto(`/history/${result.prediction_id}`)
    await expect(page.getByRole('heading', { name: 'Saved assessment' })).toBeVisible()
    await expect(page.locator('.consultation-candidate')).toHaveCount(result.primary_prediction ? 1 : 0)
    expect(await page.locator('.hist35-result-section').textContent()).not.toMatch(/\d+(?:\.\d+)?%/)
    if (result.primary_prediction) {
      await expect(page.getByRole('heading', { name: result.primary_prediction.display_name, exact: true })).toBeVisible()
    }

  })
}

for (const text of ['I am struggling to breathe.', 'Nashindwa kupumua.']) {
  test(`emergency guidance precedes the consultation: ${text}`, async ({ page }, testInfo) => {
    if (text.startsWith('Nashindwa')) await page.setViewportSize({ width: 390, height: 844 })
    const mapped = await mapInput(page, text)
    expect(mapped.has_red_flag).toBe(true)
    const alert = page.getByRole('alert')
    await expect(alert).toContainText(mapped.health_guidance)
    await expect(alert).toBeFocused()
    const bounds = await alert.boundingBox()
    const header = await page.getByRole('banner').boundingBox()
    expect(bounds.y).toBeGreaterThanOrEqual(header.y + header.height)
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(page.viewportSize().height)
    await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
    await page.screenshot({ path: `../audit-artifacts/kenya-patient-ui/after-urgent-focused-${text.startsWith('Nashindwa') ? 'mobile' : 'desktop'}.png` })
    await testInfo.attach('actual-urgent-mapping', { body: JSON.stringify(mapped, null, 2), contentType: 'application/json' })
    if (text.startsWith('I am')) {
      await page.screenshot({ path: '../audit-artifacts/kenya-patient-ui/after-urgent-desktop.png', fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      await page.screenshot({ path: '../audit-artifacts/kenya-patient-ui/after-urgent-mobile.png', fullPage: true })
    }
  })
}

test('vague input asks for symptoms without inventing a possible disease', async ({ page }, testInfo) => {
  const mapped = await mapInput(page, 'I feel unwell.')
  expect(mapped.recognised_symptoms).toEqual([])
  await expect(page.getByText('No supported symptoms were recognised')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
  await testInfo.attach('actual-insufficient-mapping', { body: JSON.stringify(mapped, null, 2), contentType: 'application/json' })
  await page.screenshot({ path: '../audit-artifacts/kenya-patient-ui/after-insufficient-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: '../audit-artifacts/kenya-patient-ui/after-insufficient-mobile.png', fullPage: true })
})

test('an old abstention cache cannot replace a new consultation', async ({ page }) => {
  const text = 'I have a cough and fever.'
  await mapInput(page, text)
  await begin(page)
  await page.evaluate((inputText) => {
    sessionStorage.setItem('respiracare_prediction_result', JSON.stringify({
      cache_version: 'assessment-2026-10-27', input_text: inputText,
      confirmed_codes: ['cough', 'fever'], status: 'insufficient_evidence', predictions: [],
    }))
  }, text)
  await page.reload()
  await expect(page.getByLabel('Age', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('respiracare_prediction_result'))).toBeNull()
})

test('empty symptom descriptions stay on the form with a readable correction', async ({ page }) => {
  await page.goto('/symptoms')
  await page.getByRole('button', { name: 'Analyse symptoms', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Please describe at least one symptom')
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
})
