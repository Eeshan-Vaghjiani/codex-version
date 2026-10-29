# RespiraCare — local manual checks

Updated 28 October 2026 for the single-primary patient flow. These are software behavior examples, not a clinical diagnosis reference set.

Open **http://127.0.0.1:5173**. You can register a local test account or use the test login previously provided. Start a fresh assessment so you do not reuse an old session. For repeatable results use **age 21, sex M**, confirm only symptoms actually reported, and answer **No** to the breathing question and **Not sure** to other unreported questions. Honest different answers can change the outcome.

| Type this | What to check |
|---|---|
| `I have intense coughing fits and vomiting after coughing for 5 days.` | After the breathing question: one possible **Whooping cough**, a clear possibility/diagnosis distinction and professional assessment advice. No percentages or extra disease cards. |
| `I have cough and a sore throat.` | After breathing and duration clarification: one possible broad **Nose or throat infection (URTI)** under the answer pattern above. No claim of confirmed influenza. |
| `I have a headache and feel tired.` | Relevant duration/severity/associated-symptom questions, then a calm explanation that these symptoms can have several causes. No forced tumour/TB label. |
| `I have fever, cough, sore throat and body aches for two days.` | A few relevant questions; under the answer pattern above, uncertainty without forcing influenza or a specific virus. |
| `Nina kikohozi lakini sina homa.` | Cough present, fever absent, Kiswahili follow-ups/guidance; “no fever” must not become positive fever. |
| `My muscles ache all over my body.` | Muscle aches recognized, followed by relevant questions; no disease forced from aches alone. |
| `I feel unwell.` | Ask for actual symptoms and duration; no invented condition. |
| `I have abdominal pain and nausea.` | Unsupported respiratory-model scope is handled clearly; no invented diagnosis. |
| `I have cough but I do not have cough.` | Contradictory cough remains uncertain rather than simultaneously present and absent. |
| `I am struggling to breathe.` or `Siwezi kupumua.` | Immediate prominent urgent assessment guidance. No routine prediction or questionnaire delay. |
| `I have a headache, fever and a stiff neck.` | Immediate urgent guidance, without diagnosing meningitis. |
| `I have a severe sudden headache.` | Immediate urgent guidance. |
| `I have severe crushing chest pressure.` | Immediate urgent guidance, without diagnosing a heart attack. |
| `I have cough for two weeks and have lost weight without trying.` | Prompt professional review advice. A possible TB result can still appear with this more specific evidence; it must be tentative and must not replace assessment/testing. |

Also try an empty submission: the form/API should reject it without inventing a result. On a phone or narrow browser, check that the question options, primary card, warning and feedback remain readable without horizontal scrolling. Reload during a follow-up and verify the current question persists. Open history: current results should preserve the same one-primary/uncertainty decision, while older policy records should prompt a new assessment without displaying their previous three scores.

No result from these checks establishes that illness is mild or that serious conditions have been ruled out. The app has not been clinically validated for Kenyan patients. The [implementation and measured comparison report](KENYA_PATIENT_EXPERIENCE_REPORT.md) distinguishes software behavior, simulated-source metrics and remaining clinical review needs.
