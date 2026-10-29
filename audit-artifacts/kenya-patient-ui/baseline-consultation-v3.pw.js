// Real UI/API journeys against an isolated migrated/seeded V3 audit database.
// Candidate names come from the model; these tests do not invent clinical truth.
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

async function answerQuestions(page, result) {
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
    const option = question.options.find((item) => item.value === 'under_3_days') ||
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
  { name: 'English cough and fever', text: 'I have a cough and fever.', language: 'en', fever: 'present' },
  { name: 'Swahili cough and fever', text: 'Nina homa na kikohozi.', language: 'sw', fever: 'present' },
  { name: 'English negation', text: 'I have a cough, but I do not have a fever.', language: 'en', fever: 'absent' },
  { name: 'Swahili negation', text: 'Nina kikohozi lakini sina homa.', language: 'sw', fever: 'absent' },
  { name: 'cough alone', text: 'I have a cough.', language: 'en', fever: null },
  { name: 'fever alone', text: 'I have fever.', language: 'en', fever: 'present' },
]

for (const scenario of scenarios) {
  test(`useful tentative consultation: ${scenario.name}`, async ({ page, request }) => {
    await mapInput(page, scenario.text)
    const { result, asked } = await answerQuestions(page, await begin(page))
    expect(result.status).toBe('prediction_complete')
    expect(result.model_version).toBe('v3_partial_evidence')
    expect(result.predictions).toHaveLength(3)
    expect(result.uncertain).toBe(true)
    expect(result.assessment_context.language).toBe(scenario.language)
    if (scenario.fever === null) {
      const feverAnswer = result.follow_up_answers.find((answer) => answer.question_id === 'fever')
      expect(result.assessment_context.symptom_states.fever).toBe(feverAnswer?.answer === 'no' ? 'absent' : undefined)
    } else {
      expect(result.assessment_context.symptom_states.fever).toBe(scenario.fever)
    }
    expect(result.follow_up_answers).toHaveLength(asked.length)
    expect(result.next_steps.length).toBeGreaterThan(0)
    await expect(page.getByRole('heading', {
      name: scenario.language === 'sw' ? 'Hali zinazowezekana' : 'Possible explanations', exact: true,
    })).toBeVisible()
    await expect(page.getByText(result.assessment_summary, { exact: true })).toBeVisible()
    for (const candidate of result.predictions) {
      await expect(page.getByRole('heading', { name: candidate.display_name, exact: true })).toBeVisible()
      expect(Array.isArray(candidate.supporting_symptoms)).toBe(true)
      expect(Array.isArray(candidate.contradicting_symptoms)).toBe(true)
      expect([...candidate.supporting_symptoms, ...candidate.contradicting_symptoms]
        .every((symptom) => typeof symptom === 'string' && !/^E_\d/.test(symptom))).toBe(true)
      expect(candidate.explanation).toBeTruthy()
    }
    await expect(page.getByText('No disease prediction is supported')).toHaveCount(0)
    // Percentages can be inspected deliberately, never in the primary result.
    for (const detail of await page.locator('.consultation-model-details p').all()) {
      await expect(detail).not.toBeVisible()
    }
    if (scenario.name === 'English cough and fever') {
      await page.screenshot({ path: 'playwright-results/v3-consultation-result.png', fullPage: true })
    }
    const token = await page.evaluate(() => sessionStorage.getItem('respiracare_access_token'))
    const history = await request.get(`${apiURL}/history/${result.prediction_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(history.ok(), await history.text()).toBe(true)
    const saved = await history.json()
    expect(saved.predictions).toEqual(result.predictions)
    expect(saved.assessment_context.symptom_states.fever).toBe(result.assessment_context.symptom_states.fever)
    await page.goto(`/history/${result.prediction_id}`)
    await expect(page.getByRole('heading', { name: 'Saved possible explanations' })).toBeVisible()
    for (const candidate of result.predictions) {
      await expect(page.getByRole('heading', { name: candidate.display_name, exact: true })).toBeVisible()
    }
  })
}

for (const text of ['I am struggling to breathe.', 'Nashindwa kupumua.']) {
  test(`emergency guidance precedes the consultation: ${text}`, async ({ page }) => {
    const mapped = await mapInput(page, text)
    expect(mapped.has_red_flag).toBe(true)
    await expect(page.getByRole('alert')).toContainText(mapped.health_guidance)
    await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
  })
}

test('vague input asks for symptoms without inventing a possible disease', async ({ page }) => {
  const mapped = await mapInput(page, 'I feel unwell.')
  expect(mapped.recognised_symptoms).toEqual([])
  await expect(page.getByText('No supported symptoms were recognised')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
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
