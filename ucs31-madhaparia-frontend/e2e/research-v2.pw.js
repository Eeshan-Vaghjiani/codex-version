// Requires V2 explicitly activated in an isolated test database.
import { expect, test } from '@playwright/test'

test('live V2 research candidates retain uncertainty, context and history', async ({ page, request }) => {
  const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000'
  const email = `audit-v2-browser-${Date.now()}@example.com`
  const password = 'Audit-test-only-2026!'
  const registration = await request.post(`${apiURL}/auth/register`, { data: { email, password } })
  expect(registration.ok(), await registration.text()).toBe(true)
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.goto('/symptoms')
  await page.getByLabel('Symptom description').fill(
    'I have a cough, fever, runny nose and sore throat for two days. I do not have difficulty breathing.',
  )
  await page.getByRole('button', { name: 'Analyse symptoms', exact: true }).click()
  await page.getByRole('link', { name: 'Continue to confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm selected symptoms' }).click()
  await page.getByRole('link', { name: 'Continue to prediction' }).click()
  await page.getByLabel('Age', { exact: true }).fill('21')
  await page.getByLabel('Sex', { exact: true }).selectOption('F')
  const resultPromise = page.waitForResponse((response) =>
    response.url().endsWith('/predict') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  const resultResponse = await resultPromise
  expect(resultResponse.ok(), await resultResponse.text()).toBe(true)
  const result = await resultResponse.json()
  expect(result.status).toBe('prediction_complete')
  expect(result.model_version).toMatch(/v2/i)
  expect(result.predictions).toHaveLength(3)
  expect(result.uncertain).toBe(true)
  expect(result.clinical_validation).toBe(false)
  expect(result.assessment_context.symptom_states.shortness_of_breath).toBe('absent')
  expect(result.assessment_context.duration.min_days).toBe(2)
  expect(result.assessment_context.duration.max_days).toBe(2)
  await expect(page.getByRole('status')).toContainText('has not been clinically validated')
  await expect(page.locator('.consultation-model-details').first()).toBeVisible()
  await expect(page.locator('.consultation-model-details p').first()).not.toBeVisible()
  for (const candidate of result.predictions) {
    await expect(page.getByText(candidate.display_name, { exact: true })).toBeVisible()
    expect(candidate.model_confidence_percent).toBeGreaterThanOrEqual(0)
    expect(candidate.model_confidence_percent).toBeLessThanOrEqual(100)
  }
  await expect(page.getByRole('list', { name: 'Ranked possible explanations' })).toBeVisible()
  await expect(page.getByRole('note', { name: 'Assessment context limitations' })).toContainText('not trained')
  await page.screenshot({ path: 'playwright-results/v2-research-result.png', fullPage: true })
  await page.goto(`/history/${result.prediction_id}`)
  await expect(page.getByRole('heading', { name: 'Saved possible explanations' })).toBeVisible()
  await expect(page.getByText(result.predictions[0].display_name, { exact: true })).toBeVisible()
  await expect(page.locator('.consultation-model-details').first()).toBeVisible()
  await expect(page.locator('.consultation-model-details p').first()).not.toBeVisible()
  await expect(page.getByRole('status')).toContainText('has not been clinically validated')
})
