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

async function begin(page, age = 21) {
  await page.getByRole('link', { name: 'Continue to confirmation' }).click()
  await page.getByRole('button', { name: 'Confirm selected symptoms' }).click()
  await page.getByRole('link', { name: 'Continue to prediction' }).click()
  await page.getByLabel('Age', { exact: true }).fill(String(age))
  await page.getByLabel('Sex', { exact: true }).selectOption('M')
  const next = page.waitForResponse((response) => response.url().endsWith('/predict'))
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  const response = await next
  expect(response.ok(), await response.text()).toBe(true)
  return response.json()
}

async function answerQuestions(page, result, preferUnknown = false, choices = {}) {
  const asked = []
  while (result.status === 'needs_follow_up') {
    const question = result.follow_up_question
    expect(asked).not.toContain(question.id)
    asked.push(question.id)
    expect(asked.length).toBeLessThanOrEqual(20)  // uncapped gathering: soft guide 5, hard ceiling 20
    await expect(page.getByRole('heading', { name: question.text, exact: true })).toBeVisible()
    if (asked.length === 1) {
      await page.reload()
      await expect(page.getByRole('heading', { name: question.text, exact: true })).toBeVisible()
    }
    const option = question.options.find((item) => item.value === choices[question.id]) || (preferUnknown && !/breath/.test(question.id) &&
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
  { name: 'common four-symptom family', text: 'I have cough, sore throat, runny nose and headache', language: 'en', requiresFamily: true },
]

for (const scenario of scenarios) {
  test(`single-primary policy: ${scenario.name}`, async ({ page, request }, testInfo) => {
    await mapInput(page, scenario.text)
    const { result, asked } = await answerQuestions(page, await begin(page), scenario.requiresPrimary)
    expect(['prediction_complete', 'assessment_uncertain', 'insufficient_evidence']).toContain(result.status)
    expect(result.decision.policy_version).toBeTruthy()
    expect(result.predictions.length).toBeLessThanOrEqual(1)
    if (scenario.requiresFamily) {
      expect(result.primary_prediction?.is_family_answer).toBe(true)
      expect(result.primary_prediction.condition).toBe('Flu-like illness / common cold')
    }
    if (scenario.requiresPrimary) {
      expect(result.primary_prediction).toBeNull()
      expect(result.decision.reasons).toContain('gap_source_validation_bound_not_met')
    }
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
        name: result.withheld_title || (scenario.language === 'sw' ? 'Tunahitaji maelezo zaidi' : 'More information is needed'), exact: true,
      })).toBeVisible()
      await expect(page.locator('.consultation-candidate')).toHaveCount(0)
    }
    await expect(page.locator('.pred34-result-intro').getByText(result.assessment_summary, { exact: true })).toBeVisible()
    if (result.primary_prediction) {
      if (result.primary_prediction.is_family_answer) {
        // A family answer names a family, never a specific virus; it carries
        // no model match percentage.
        expect(result.primary_prediction.model_match_percent).toBeNull()
        expect(result.predictions).toEqual([result.primary_prediction])
        await expect(page.locator('.consultation-match')).toHaveCount(0)
      } else {
        expect(Number.isInteger(result.primary_prediction.model_match_percent)).toBe(true)
        await expect(page.getByText(/not a probability, not a diagnosis, not overall accuracy/)).toBeVisible()
      }
    } else expect(await page.locator('.pred34-results').textContent()).not.toMatch(/\d+(?:\.\d+)?%/)
    expect(JSON.stringify(result)).not.toMatch(/model_confidence_percent|raw_relative_score/)
    if (['informative coughing fits', 'English cough and fever', 'headache and tiredness', 'fever cough sore throat body aches'].includes(scenario.name)) {
      const slug = scenario.name.toLowerCase().replaceAll(' ', '-')
      await page.screenshot({ path: `../audit-artifacts/validation-2026-10-29-ui/after-${slug}-desktop.png`, fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      await page.screenshot({ path: `../audit-artifacts/validation-2026-10-29-ui/after-${slug}-mobile.png`, fullPage: true })
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
    await page.screenshot({ path: `../audit-artifacts/validation-2026-10-29-ui/after-urgent-focused-${text.startsWith('Nashindwa') ? 'mobile' : 'desktop'}.png` })
    await testInfo.attach('actual-urgent-mapping', { body: JSON.stringify(mapped, null, 2), contentType: 'application/json' })
    if (text.startsWith('I am')) {
      await page.screenshot({ path: '../audit-artifacts/validation-2026-10-29-ui/after-urgent-desktop.png', fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      await page.screenshot({ path: '../audit-artifacts/validation-2026-10-29-ui/after-urgent-mobile.png', fullPage: true })
    }
  })
}

test('vague input asks for symptoms without inventing a possible disease', async ({ page }, testInfo) => {
  const mapped = await mapInput(page, 'I feel unwell.')
  expect(mapped.recognised_symptoms).toEqual([])
  await expect(page.getByText('No supported symptoms were recognised')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
  await testInfo.attach('actual-insufficient-mapping', { body: JSON.stringify(mapped, null, 2), contentType: 'application/json' })
  await page.screenshot({ path: '../audit-artifacts/validation-2026-10-29-ui/after-insufficient-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: '../audit-artifacts/validation-2026-10-29-ui/after-insufficient-mobile.png', fullPage: true })
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

// Real UI/API regressions; expected abstention reflects the pending gap fold,
// not a judgement that these symptoms are harmless or that COVID is excluded.
const safetyJourneys = [
  ['headache-fatigue', 'I have headache and fatigue'],
  ['cough', 'Nina kikohozi'],
  ['fever-cough-2d', 'I have fever na kikohozi for two days'],
  ['viral-2d', 'I have fever, cough and tiredness for two days'],
  ['prolonged-weight', 'I have cough for three weeks and unintentional weight loss'],
  ['cannot-breathe-en', "I can't breathe", 'emergency'],
  ['cannot-breathe-sw', 'Siwezi kupumua', 'emergency'],
  ['exertion', 'I have difficulty breathing when I walk, but I can speak fine', 'urgent_same_day'],
  ['difficulty-sw', 'Napumua kwa shida', 'urgent_same_day'],
  ['negative-breathing', 'I can breathe fine and have a cough'],
  ['smell', 'I have loss of smell'],
  ['smell-viral', 'I have loss of smell, cough and fever'],
  ['taste', 'I have loss of taste and fever'],
  ['chest-pain', 'I have severe chest pain', 'emergency'],
  ['fainting', 'I fainted', 'emergency'],
  ['blue-lips', 'My lips are turning blue', 'emergency'],
  ['blood', 'I am coughing a lot of blood', 'emergency'],
  ['confusion', 'I have confusion', 'emergency'],
  ['baby-fever', 'I have fever', 'emergency', 0],
  ['baby-fever-after-smell-loss', 'I have no sense of smell, fever and cough', 'emergency', 0],
  ['stiff-neck', 'I have headache, fever and stiff neck', 'emergency'],
  ['generic', 'I have fever, pain and fatigue'],
  ['severe-viral', 'I have severe fever, cough and body aches for two days'],
  ['overlap', 'I have cough, sore throat, fever and muscle aches'],
  ['sw-mixed', 'Nina homa na cough kwa siku mbili'],
]

for (const [name, text, urgency, age = 24] of safetyJourneys) {
  test(`P0 journey: ${name}`, async ({ page }, testInfo) => {
    const mapping = await mapInput(page, text)
    let result = mapping
    if (mapping.has_red_flag) {
      expect(mapping.urgency).toBe(urgency)
      await expect(page.getByRole('alert')).toContainText(mapping.health_guidance)
      await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
      if (mapping.safety_question) {
        const next = page.waitForResponse((response) => response.url().endsWith('/nlp/map'))
        await page.getByRole('button', { name: mapping.safety_question.options.find((option) => option.value === 'exertion_full_sentence').label, exact: true }).click()
        result = await (await next).json()
        expect(result.urgency).toBe('urgent_same_day')
        expect(result.safety_question).toBeNull()
      } else expect(mapping.safety_question).toBeNull()
    } else {
      result = (await answerQuestions(page, await begin(page, age))).result
      if (name === 'overlap') {
        // The 4-present viral upper-respiratory cluster now resolves to an
        // honest family answer, never a specific disease or a model match %.
        expect(result.primary_prediction).not.toBeNull()
        expect(result.primary_prediction.is_family_answer).toBe(true)
        expect(result.primary_prediction.condition).toBe('Flu-like illness / common cold')
        expect(result.primary_prediction.model_match_percent).toBeNull()
        expect(result.predictions).toEqual([result.primary_prediction])
        await expect(page.getByRole('heading', {
          name: result.primary_prediction.display_name, exact: true })).toBeVisible()
        await expect(page.locator('.consultation-candidate')).toHaveCount(1)
        return
      }
      expect(result.primary_prediction).toBeNull()
      expect(result.predictions).toEqual([])
      if (urgency) {
        expect(result.urgency).toBe(urgency)
        expect(result.follow_up_question).toBeUndefined()
      } else {
        expect(result.uncertainty_message).toMatch(/nothing is ruled out|hakuna ugonjwa ulioondolewa/)
        expect(result.uncertainty_message).toContain('24-48')
      }
      await expect(page.getByRole('heading', { name: 'What we understood / Tulichoelewa' })).toBeVisible()
      await expect(page.getByLabel(/Correct symptoms, duration or severity/)).toBeVisible()
      await expect(page.getByRole('button', { name: /Recheck corrections/ })).toBeVisible()
      await expect(page.getByRole('note').filter({ hasText: /COVID/ })).toBeVisible()
    }
    await expect(page.locator('.consultation-candidate')).toHaveCount(0)
    await testInfo.attach('journey-output', { body: JSON.stringify({ name, expected: {
      primary: 'withheld', score_band: 'not shown', urgency: urgency || 'advice-dependent',
    }, actual: result }, null, 2), contentType: 'application/json' })
  })
}

for (const text of ['i feel tired and have weaknes for 3 days',
  'Ninahisi uchovu na sina nguvu kwa siku tatu', 'Nina uchovu na weakness kwa siku tatu']) {
  test(`everyday conversation: ${text}`, async ({ page, context }, testInfo) => {
    await mapInput(page, text)
    const { result, asked } = await answerQuestions(page, await begin(page, 24), false, {
      weakness_meaning: 'general_low_energy', symptom_severity: 'mild',
    })
    expect(result.primary_prediction).toBeNull()
    expect(result.assessment_context.duration.min_days).toBe(3)
    expect(result.assessment_context.symptom_states.weakness).toBe('present')
    expect(result.model_features).toEqual([])
    expect(asked).toContain('weakness_meaning')
    expect(asked.length).toBeLessThanOrEqual(20)  // uncapped gathering: soft guide 5, hard ceiling 20
    expect(result.next_steps.join(' ')).not.toMatch(/influenza|pneumonia|covid|bronchitis|malaria/i)
    await expect(page.getByLabel(/Correct symptoms, duration or severity/)).toHaveValue(text)
    await page.getByText('Summary to show a health worker / Muhtasari kwa mhudumu wa afya', { exact: true }).click()
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await page.getByRole('button', { name: 'Copy summary / Nakili muhtasari' }).click()
    await expect(page.getByText(/Copied. Only share/)).toBeVisible()
    expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(text)
    await testInfo.attach('actual-conversation', { body: JSON.stringify(result, null, 2), contentType: 'application/json' })
  })
}

test('weakness clarification escalates sudden one-sided change without another question', async ({ page }) => {
  await mapInput(page, 'I feel weak for three days')
  const { result } = await answerQuestions(page, await begin(page, 24), false, { weakness_meaning: 'sudden_one_sided' })
  expect(result.urgency).toBe('emergency')
  expect(result.primary_prediction).toBeNull()
  expect(result.follow_up_question).toBeUndefined()
  await expect(page.getByRole('alert')).toContainText('hospital casualty')
  await expect(page.getByRole('radio')).toHaveCount(0)
})

test('reported sudden one-sided weakness stops immediately at symptom entry', async ({ page }) => {
  const mapping = await mapInput(page, 'I have sudden one-sided weakness')
  expect(mapping.urgency).toBe('emergency')
  expect(mapping.safety_question).toBeNull()
  await expect(page.getByRole('alert')).toContainText('hospital casualty')
  await expect(page.getByRole('link', { name: 'Continue to confirmation' })).toHaveCount(0)
})

test('a richer eligible pattern displays one whole-percent match and preserves it in history', async ({ page, request }, testInfo) => {
  await mapInput(page, 'I have fever, cough, sore throat, muscle aches, constant tiredness and runny nose for two days')
  const { result } = await answerQuestions(page, await begin(page))
  expect(result.status).toBe('prediction_complete')
  expect(result.predictions).toEqual([result.primary_prediction])
  expect(Number.isInteger(result.primary_prediction.model_match_percent)).toBe(true)
  expect(result.primary_prediction.model_match_percent).toBeGreaterThanOrEqual(60)
  await expect(page.locator('.consultation-candidate')).toHaveCount(1)
  await expect(page.getByText(/not a probability, not a diagnosis, not overall accuracy/)).toBeVisible()
  const token = await page.evaluate(() => sessionStorage.getItem('respiracare_access_token'))
  const history = await request.get(`${apiURL}/history/${result.prediction_id}`, { headers: { Authorization: `Bearer ${token}` } })
  expect(history.ok()).toBe(true)
  expect((await history.json()).primary_prediction).toEqual(result.primary_prediction)
  await page.goto(`/history/${result.prediction_id}`)
  await expect(page.locator('.consultation-candidate')).toHaveCount(1)
  await expect(page.getByText(new RegExp(`Model match: ${result.primary_prediction.model_match_percent}%`))).toBeVisible()
  await testInfo.attach('actual-eligible-match', { body: JSON.stringify(result, null, 2), contentType: 'application/json' })
})

test('result correction rechecks safety and clears the old assessment', async ({ page }) => {
  await mapInput(page, 'I feel tired and have weakness for three days')
  await answerQuestions(page, await begin(page, 24), false, { weakness_meaning: 'general_low_energy', symptom_severity: 'mild' })
  await page.getByLabel(/Correct symptoms, duration or severity/).fill('I have sudden one-sided weakness')
  await page.getByRole('button', { name: /Recheck corrections/ }).click()
  await expect(page.getByRole('alert')).toContainText('hospital casualty')
  expect(await page.evaluate(() => sessionStorage.getItem('respiracare_prediction_result'))).toBeNull()
  expect(await page.evaluate(() => sessionStorage.getItem('respiracare_symptom_confirmation'))).toBeNull()
})

test('added discriminator symptoms are confirmed against updated text before prediction', async ({ page }) => {
  await mapInput(page, 'I feel weak for 3 days')
  const withheld = (await answerQuestions(page, await begin(page, 22), true)).result
  expect(withheld.primary_prediction).toBeNull()
  for (const code of ['cough', 'sore_throat', 'runny_blocked_nose']) {
    const question = withheld.discriminator_questions.find((item) => item.code === code)
    expect(question).toBeTruthy()
    await page.getByRole('group', { name: question.text_en }).getByRole('radio', { name: 'Yes', exact: true }).check()
  }
  const confirmed = page.waitForResponse((response) => response.url().endsWith('/symptoms/confirm'))
  await page.getByRole('button', { name: 'Submit and re-assess' }).click()
  const confirmationResponse = await confirmed
  expect(confirmationResponse.ok(), await confirmationResponse.text()).toBe(true)
  const confirmation = await confirmationResponse.json()
  expect(confirmation.confirmed_codes.sort()).toEqual(['weakness', 'cough', 'sore_throat', 'runny_blocked_nose'].sort())
  await expect(page.getByRole('heading', { name: 'Complete your information' })).toBeVisible()
  const next = page.waitForResponse((response) => response.url().endsWith('/predict'))
  await page.getByRole('button', { name: 'Generate awareness result' }).click()
  const response = await next
  expect(response.ok(), await response.text()).toBe(true)
  const sent = response.request().postDataJSON()
  expect(sent.text).toContain('I have a cough.')
  expect(sent.text).toContain('I have a sore throat.')
  expect(sent.text).toContain('I have a runny or blocked nose.')
  const result = (await answerQuestions(page, await response.json(), false, {
    weakness_meaning: 'general_low_energy', symptom_severity: 'mild',
  })).result
  expect(['assessment_uncertain', 'prediction_complete']).toContain(result.status)
  await expect(page.getByText(/not recognised as present from the submitted text/)).toHaveCount(0)
})
