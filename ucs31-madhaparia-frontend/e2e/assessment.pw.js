// Run only against an isolated, migrated, seeded local audit database.
// These software journeys do not assert clinical disease ground truth.
import { expect, test } from '@playwright/test'

const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000'

test.beforeEach(async ({ page, request }, testInfo) => {
  const email = `audit-browser-${Date.now()}-${testInfo.testId.slice(-6)}@example.com`
  const password = 'Audit-test-only-2026!'
  const registration = await request.post(`${apiURL}/auth/register`, { data: { email, password } })
  expect(registration.ok(), await registration.text()).toBe(true)
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
})

async function analyse(page, text) {
  await page.goto('/symptoms')
  await page.getByLabel('Symptom description').fill(text)
  const response = page.waitForResponse((item) => item.url().endsWith('/nlp/map') && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analyse symptoms', exact: true }).click()
  const mapped = await response
  expect(mapped.ok(), await mapped.text()).toBe(true)
  return mapped.json()
}

async function beginAssessment(page) {
  await page.getByRole('link', { name: 'Continue to confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm selected symptoms' }).click()
  await page.getByRole('link', { name: 'Continue to prediction' }).click()
  await page.getByLabel('Age', { exact: true }).fill('21')
  await page.getByLabel('Sex', { exact: true }).selectOption('M')
  const response = page.waitForResponse((item) => item.url().endsWith('/predict') && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  return (await response).json()
}

async function finishQuestions(page, response) {
  const ids = []
  while (response.status === 'needs_follow_up') {
    const question = response.follow_up_question
    expect(ids).not.toContain(question.id)
    ids.push(question.id)
    expect(ids.length).toBeLessThanOrEqual(5)
    await expect(page.getByRole('heading', { name: question.text })).toBeVisible()
    const answer = question.id === 'symptom_duration' ? 'under_3_days' : 'no'
    const option = question.options.find((item) => item.value === answer)
    await page.getByRole('radio', { name: option.label, exact: true }).check()
    const next = page.waitForResponse((item) => item.url().endsWith('/predict') && item.request().method() === 'POST')
    await page.getByRole('button', { name: 'Continue / Endelea' }).click()
    response = await (await next).json()
  }
  return { response, ids }
}

for (const scenario of [
  { language: 'en', text: 'I have a cough, but I do not have a fever.', fever: 'absent' },
  { language: 'sw', text: 'Nina kikohozi lakini sina homa.', fever: 'absent' },
  { language: 'sw', text: 'Nina homa na kikohozi.', fever: 'present' },
]) {
  test(`live ${scenario.language} symptoms, negation, follow-ups, reload and history: ${scenario.fever}`, async ({ page, request }) => {
    const mapped = await analyse(page, scenario.text)
    expect(mapped.recognised_symptoms.find((item) => item.code === 'cough').status).toBe('present')
    expect(mapped.recognised_symptoms.find((item) => item.code === 'fever').status).toBe(scenario.fever)
    let response = await beginAssessment(page)
    expect(response.status).toBe('needs_follow_up')
    await page.reload()
    await expect(page.getByRole('heading', { name: response.follow_up_question.text })).toBeVisible()
    const finished = await finishQuestions(page, response)
    response = finished.response
    expect(response.status).toBe('insufficient_evidence') // Audit DB runs production V1.
    expect(response.predictions).toEqual([])
    expect(response.age).toBe(21)
    expect(response.sex).toBe('M')
    expect(response.assessment_context.language).toBe(scenario.language)
    expect(response.assessment_context.symptom_states.cough).toBe('present')
    expect(response.assessment_context.symptom_states.fever).toBe(scenario.fever)
    expect(response.assessment_context.duration.min_days).toBe(0)
    expect(response.assessment_context.follow_up_answers).toHaveLength(finished.ids.length)
    await expect(page.getByText('No disease prediction is supported')).toBeVisible()
    await expect(page.getByRole('note', { name: 'Assessment context limitations' })).toBeVisible()
    const token = await page.evaluate(() => sessionStorage.getItem('respiracare_access_token'))
    const history = await request.get(`${apiURL}/history/${response.prediction_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(history.ok(), await history.text()).toBe(true)
    const stored = await history.json()
    expect(stored.assessment_context.symptom_states.fever).toBe(scenario.fever)
    expect(stored.assessment_context.follow_up_answers).toEqual(response.follow_up_answers)
  })
}

for (const text of ['I have a cough and I am struggling to breathe.', 'Nashindwa kupumua.']) {
  test(`live emergency guidance before confirmation: ${text}`, async ({ page }) => {
    const mapped = await analyse(page, text)
    expect(mapped.has_red_flag).toBe(true)
    await expect(page.getByRole('alert')).toContainText(mapped.health_guidance)
    await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
    await expect(page.getByRole('radio')).toHaveCount(0)
  })
}

test('live vague input asks for clearer symptoms without forcing a diagnosis', async ({ page }) => {
  const mapped = await analyse(page, 'I feel unwell.')
  expect(mapped.recognised_symptoms).toEqual([])
  await expect(page.getByText('No supported symptoms were recognised')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
})

test('legacy cached TB result cannot reopen as a current cough-and-fever assessment', async ({ page }) => {
  const text = 'I have a cough and fever.'
  await analyse(page, text)
  await beginAssessment(page)
  await page.evaluate((inputText) => {
    sessionStorage.setItem('respiracare_prediction_result', JSON.stringify({
      input_text: inputText, confirmed_codes: ['cough', 'fever'],
      status: 'prediction_complete', prediction_id: 'historical-cache',
      predictions: [{ rank: 1, condition: 'Tuberculosis', display_name: 'Tuberculosis (TB)',
        model_confidence_percent: 99.75, description: 'Legacy model output' }],
    }))
  }, text)
  await page.reload()
  await expect(page.getByText('Tuberculosis (TB)', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Age', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('respiracare_prediction_result'))).toBeNull()
  await page.getByLabel('Age', { exact: true }).fill('21')
  await page.getByLabel('Sex', { exact: true }).selectOption('M')
  const next = page.waitForResponse((item) => item.url().endsWith('/predict') && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  const { response } = await finishQuestions(page, await (await next).json())
  expect(response.status).toBe('insufficient_evidence')
  expect(response.predictions).toEqual([])
  await expect(page.getByText('No disease prediction is supported')).toBeVisible()
})
