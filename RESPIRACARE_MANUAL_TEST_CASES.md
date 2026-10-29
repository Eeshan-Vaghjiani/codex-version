# RespiraCare — local manual checks

Updated 29 October 2026. These are synthetic software behaviour cases, not clinical diagnoses or Kenyan validation.

Use an isolated local V3 API and frontend, register a disposable account, and start a fresh assessment. For the recorded new browser journeys use **age 24, sex M**, except the baby case (**age 0**). Confirm only present patient symptoms. Answer **No** to unreported breathing difficulty, severe chest pain and fever; **under 3 days** only for an otherwise unspecified duration in these synthetic cases; **Not sure** to other unreported questions. These are a reproducible test-answer pattern, not suggested patient answers. Real users must answer honestly.

**Current naming/score expectation.** Names require the checked V3 bucket + scope
+ gap policy. A predeclared 0.15 gap / 0.60 floor passed 24 of 48 evidence buckets
on a separate source-validation fold: 5–8 positive-feature buckets may show one
whole-percent V3 model match (not a probability or overall accuracy), while the
1–3 positive-feature buckets remain withheld with no score. Do not restore an old
name to make a demo look better. The rows below follow that rule: sparse input is
withheld, the richer eligible pattern shows one match.

| Case | Input | Expected urgency and next advice | Recorded browser outcome |
|---|---|---|---|
| Headache + fatigue failure case | `I have headache and fatigue` | Uncertain; no tumour/TB name; nothing ruled out, monitor 24–48h, sooner if worsening; correct extraction | PASS |
| Cough only | `Nina kikohozi` | Safety screen first; uncertain, same monitoring/correction advice | PASS |
| Fever + cough, 2 days | `I have fever na kikohozi for two days` | Uncertain; acute-infection advice, ask about malaria testing with fever in Kenya | PASS |
| Fever + cough + tiredness | `I have fever, cough and tiredness for two days` | Uncertain; acute advice, not confirmed influenza/COVID | PASS |
| Prolonged cough + weight loss | `I have cough for three weeks and unintentional weight loss` | Professional assessment promptly; persistent-cough/TB testing advice, no TB diagnosis | PASS |
| Cannot breathe, English | `I can't breathe` | Emergency, nearest hospital casualty immediately; no prediction or questions | PASS |
| Cannot breathe, Kiswahili | `Siwezi kupumua` | Same immediate emergency advice, in Kiswahili | PASS |
| Exertion with normal speech | `I have difficulty breathing when I walk, but I can speak fine` | Urgent same-day care; no routine prediction; emergency if at rest/cannot speak | PASS |
| Ambiguous breathing difficulty | `Napumua kwa shida` | Same-day advice plus exactly one exertion/speech check; exertion+full sentence stays same-day, rest/cannot speak becomes emergency | PASS |
| Breathing denial + cough | `I can breathe fine and have a cough` | No false breathing red flag; routine safety checks, withheld, monitor/correct | PASS |
| Smell only | `I have loss of smell` | Withheld; COVID outside scope, test recommendation; never a COVID label | PASS |
| Smell + cough + fever | `I have loss of smell, cough and fever` | Withheld; sinusitis/flu-like pattern does not exclude COVID; testing advice | PASS |
| Taste + fever | `I have loss of taste and fever` | Unsupported taste is not COVID proof; COVID testing advice; fever/malaria advice | PASS |
| Severe chest pain | `I have severe chest pain` | Emergency casualty now; stop questions and prediction | PASS |
| Fainting | `I fainted` | Emergency casualty now | PASS |
| Blue lips | `My lips are turning blue` | Emergency casualty now | PASS |
| A lot of blood | `I am coughing a lot of blood` | Emergency casualty now | PASS |
| Confusion | `I have confusion` | Emergency casualty now | PASS |
| Baby fever | `I have fever`, **age 0** | Immediate clinical assessment/casualty; no further questions or model guess | PASS |
| Headache + fever + stiff neck | `I have headache, fever and stiff neck` | Emergency casualty now, no diagnosis of the cause | PASS |
| Generic nonrespiratory input | `I have fever, pain and fatigue` | No respiratory name; nothing ruled out, monitor/review/correct | PASS |
| Severe flu-like illness, no test | `I have severe fever, cough and body aches for two days` | Professional review; no automatic COVID label | PASS |
| Overlapping respiratory pattern | `I have cough, sore throat, fever and muscle aches` | Withheld, not blindly highest-ranked; COVID caveat and monitoring. Separate mocked close-gap/dangerous-second units verify same-day review | PASS |
| Additional mixed input | `Nina homa na cough kwa siku mbili` | Kiswahili/mixed safety screen, acute advice, withheld | PASS |
| Flu claim, English | `I have flu` | Flu-like guidance (rest/fluids/paracetamol, no antibiotics); no condition named; COVID-test consideration if fever/chills | PASS |
| Flu claim, Kiswahili/Sheng | `niko na flu` | Same flu-like guidance in Kiswahili; no condition named | PASS |
| Cold claim | `I have a cold` / `niko na cold` | Viral-cold guidance (upper-respiratory, rest/fluids/paracetamol, 5-7 day review); no condition named | PASS |
| Everyday Sheng symptoms | `kifua kinauma` / `kichwa kinauma` / `koo inaniuma` / `pua inanitoka` / `naskia mwili` | Each symptom understood and confirmed; no unmatched wording; safety screen still first | PASS |
| Tiredness + cough + fever | `nina kikohozi na homa na nimechoka` | All three understood; fatigue-pattern asked; withheld (sparse), actionable acute advice, nothing ruled out | PASS |
| Dizziness (context) | `i am dizzy` / `nina kizunguzungu` | Dizziness understood as context (no model evidence); safety screen first; never faked into a prediction | PASS |
| Night sweats | `i sweat at night` | Recognised as heavy sweating; no unmatched wording | PASS |
| Sparse guidance is symptom-aware | `I have tiredness, headache and fever` (under 3 days, moderate) | Withheld (no name), but guidance is tailored: headache+fever stiff-neck/confusion red-flag line, tiredness line, malaria-test line; no diagnosis named | PASS |

Additional recorded journeys:

| Case | Input | Expected | Recorded browser outcome |
|---|---|---|---|
| Everyday weakness, typo | `i feel tired and have weaknes for 3 days` | Both symptoms recognised; weakness clarification; no respiratory advice despite 3 days; no name/score | PASS |
| Everyday weakness, Kiswahili | `Ninahisi uchovu na sina nguvu kwa siku tatu` | Same neutral outcome, Kiswahili | PASS |
| Everyday weakness, mixed | `Nina uchovu na weakness kwa siku tatu` | Same neutral outcome | PASS |
| Weakness clarification escalates | `I feel weak for three days`, answer sudden one-sided | Emergency, no further question, no prediction | PASS |
| Sudden one-sided weakness reported | `I have sudden one-sided weakness` | Immediate emergency at symptom entry; no confirmation link | PASS |
| Eligible rich pattern | `I have fever, cough, sore throat, muscle aches, constant tiredness and runny nose for two days` | One whole-percent V3 match (Influenza), preserved in history | PASS |
| Correction rechecks safety | `I feel tired and have weakness for three days` → correct to `I have sudden one-sided weakness` | Emergency after recheck; old result/confirmation cleared | PASS |
| Health-worker summary copy | Everyday weakness result | Copy summary contains reported text; no ranked scores | PASS |
| Common cold, everyday phrasing | `i feel cold, and my throat pains, and i have running nose` | chills/sore throat/runny nose all recognised; no name; viral-cold guidance + COVID test consideration | PASS |
| Loss of taste | `I have loss of taste` | Recognised; COVID testing advice; not a COVID diagnosis | PASS |

The original **14 browser journeys** are retained, including informative coughing fits, English/Kiswahili negations, vague input, urgent focus/viewport, stale cache and empty input. The informative case now explicitly checks source-gap withholding instead of requiring its old disease name. No scenario was deleted to hide a failure. All **45 browser journeys** ran against real local Edge + UI + API, not mocked browser responses. See the [validation record](audit-artifacts/VALIDATION_2026-10-29.md) for final counts.

Also check an empty submission; unknown wording; `my brother has a cough` (not patient evidence); `I have cough but I do not have cough` (uncertain); `Nina kikohozi lakini sina homa` (fever absent); sudden unusually severe headache; severe/crushing chest pressure. On mobile, check warning focus and readable controls. Reload during a follow-up; its question must persist. On the result, check present/absent/uncertain, duration and severity, edit the description, and recheck; the old result/confirmation must be cleared. Current history must preserve urgency and abstention; old policies require reassessment and must not resurrect scores/names.

No result establishes that illness is mild or anything is ruled out. The app is not clinically validated for Kenyan patients; clinician/Kiswahili/patient-comprehension review is pending. The [evaluation note](audit-artifacts/SIMULATED_EVALUATION_2026-10-29.md) separates retained simulated DDXPlus numbers from the blocked fresh evaluation. These browser passes do not establish medical safety, diagnostic accuracy or clinical benefit from follow-ups.
