# Kenya patient terminology and clinical scope research

Researched 28 October 2026. This is an evidence-informed implementation resource, not a clinician-reviewed assessment standard. No Kenyan clinician, Kiswahili language professional or patient comprehension panel was available for this work. English and Kiswahili wording still require that review. No source below validates this model.

## What the local implementation actually supports

`app/ml/artifacts/v3_partial_evidence.json` contains 21 respiratory source classes. `app/data/condition_information.json` has 23 presentation entries, including COVID-19 and allergic rhinitis; its membership does not establish active V3 support. That pre-existing file was preserved. The separate `patient_terminology.json` maps the exact 21 V3 keys to medical names, concise English/Kiswahili display text, descriptions and source IDs. It neither adds classes nor changes probabilities. Model metadata says the source records are simulated; they are not representative Kenyan clinical encounters.

Keep four questions separate: Is a condition relevant to Kenyan care? Is it represented in training labels? Can this active model emit that label? Has a clinician-led Kenyan study validated the prediction? For this project the last answer is **no**. A closed 21-class model cannot exclude malaria, COVID-19, HIV, meningitis, heart attack or other causes merely because they have no output class. Its score is relative to its limited class set, not the probability of all possible causes.

Kenya's national guidelines and lung-health programme establish local clinical relevance, not an ordering of probabilities for this patient. No Kenyan prevalence prior was estimated or inserted. The existing simulated label distribution cannot establish Kenyan disease frequency, geographical variation, seasonal circulation or diagnostic performance.

## Flu, influenza, common cold and URTI

“Influenza” identifies infection caused by influenza viruses; “flu” is its familiar English name. The terminology entry uses **Seasonal flu (influenza)** and explains uncertainty. This does not justify assigning influenza from fever, cough, sore throat and aches alone. WHO describes overlap with other respiratory pathogens; testing and clinical context distinguish the cause. Clinicians may make a provisional clinical diagnosis, but an app pattern is not laboratory confirmation. [WHO influenza][who_influenza], [CDC flu/COVID comparison][cdc_flu_covid], [CDC diagnosis][cdc_flu_testing].

“Common cold” is a clinical illness within the broader upper respiratory infection category. **URTI** describes the location/category of infection and does not establish a virus or influenza. **Viral respiratory infection** additionally asserts a viral cause; use “possible” when unconfirmed. Kenya's hospital guidance discusses common cold and pharyngitis under upper respiratory infections. Do not relabel the model's URTI class as influenza, a particular pathogen, or definitely a common cold. [Kenya hospital guideline, section 24.1][ke_hospitals_2024], [NHS RTIs][nhs_rti].

**Flu-like symptoms/illness** can describe a symptom pattern while leaving its cause open; it is not a new trained class and must not imply low risk. WHO's *surveillance* ILI definition uses measured fever at least 38°C, cough and onset within ten days. This population surveillance definition is not a patient diagnostic or reassurance rule; do not claim a patient meets it without the measurements and timing. A patient may need assessment despite not meeting it. [WHO surveillance definitions][who_ili]. Kiswahili draft wording keeps “influenza” explicit rather than translating every nose symptom as confirmed influenza. It is a proposed translation, not a claim that a national Kiswahili terminology standard was located.

## Presentation table

“Yes” below means an active V3 source label exists, **not** proven clinical ability. Symptoms are examples, not diagnostic criteria. Recommendations are communication/assessment guidance, not medication instructions.

| Disease or presentation | Familiar patient wording | Relevant symptoms | Differential or limitation | Active V3 support | Recommended action | Supporting source |
|---|---|---|---|---|---|---|
| Acute COPD exacerbation / infection | COPD flare-up / possible infection | More breathlessness, cough, mucus | Requires existing COPD history; infection is not established | Yes, combined class | Clinical assessment; urgent if breathing is impaired | [WHO COPD][who_copd] |
| Acute laryngitis | Voice box inflammation | Hoarseness, cough, sore throat | Hoarseness has other causes | Yes | Assess persistent symptoms; breathing trouble needs urgent care | [NHS laryngitis][nhs_laryngitis] |
| Acute pulmonary edema | Sudden fluid build-up in lungs | Sudden breathing difficulty | Heart and other lung causes need examination | Yes | Emergency assessment for sudden/severe breathing difficulty | [NHLBI][nhlbi_respiratory_failure] |
| Acute rhinosinusitis | Recent nose and sinus inflammation | Blockage, discharge, facial pressure | Viral/bacterial cause not established by symptoms | Yes | Assess worsening, severe or persistent symptoms | [NHS sinusitis][nhs_sinusitis] |
| Allergic sinusitis | Allergy-related sinus inflammation | Nasal blockage, facial pressure | Ambiguous source label; not identical to allergic rhinitis | Yes | Confirm allergy/history clinically; retain exact class key | [NHS sinusitis][nhs_sinusitis] |
| Bronchiectasis | Widened, damaged airways | Persistent productive cough, repeated infections | Needs tests; not inferable from an isolated cough | Yes | Clinical assessment rather than self-diagnosis | [NHS inform][nhs_bronchiectasis] |
| Bronchiolitis | Small airway infection | Infant cough, noisy/fast breathing, poor feeding | Mainly under two; distinguish from bronchitis | Yes | Prompt assessment for poor feeding; emergency for pauses/severe difficulty | [NHS bronchiolitis][nhs_bronchiolitis] |
| Bronchitis | Airway inflammation | Cough, mucus | Pneumonia and other respiratory illnesses overlap | Yes | Assess worsening cough, breathlessness, chest pain or blood | [NHS bronchitis][nhs_bronchitis] |
| Bronchospasm / acute asthma exacerbation | Airway narrowing / asthma flare-up | Wheeze, cough, chest tightness | Symptoms alone do not diagnose asthma | Yes, combined class | Assess breathing and existing action plan; urgent if severe | [WHO asthma][who_asthma] |
| Chronic rhinosinusitis | Ongoing nose and sinus inflammation | Ongoing blockage/discharge, reduced smell | Duration and clinical review needed | Yes | Assess persistent/recurrent symptoms | [NHS sinusitis][nhs_sinusitis] |
| Croup | Croup (upper airway swelling) | Barking cough, hoarseness, noisy breathing | Mostly young children; other airway obstruction possible | Yes | Clinical assessment; emergency for breathing distress | [NHS croup][nhs_croup] |
| Epiglottitis | Swelling near the windpipe | Rapid breathing/swallowing trouble, drooling | Can obstruct the airway | Yes | Emergency hospital care; stop questions | [NHS epiglottitis][nhs_epiglottitis] |
| Influenza | Seasonal flu (influenza) | Fever, cough, aches, sore throat | COVID-19 and other infections cannot be separated by symptoms alone | Yes | Explain possibility; clinical review/testing as indicated | [WHO influenza][who_influenza], [CDC][cdc_flu_covid] |
| Larygospasm (source spelling) | Vocal cord spasm (laryngospasm) | Sudden difficulty speaking/breathing | Correct display spelling; preserve model key | Yes | Assess cause; ongoing breathing difficulty is urgent | [Mayo Clinic][mayo_laryngospasm] |
| Pneumonia | Lung infection (pneumonia) | Cough, fever, difficult/fast breathing | Multiple pathogens; examination/severity assessment needed | Yes | Clinical assessment; urgent for breathing difficulty | [WHO pneumonia][who_pneumonia] |
| Pulmonary neoplasm | Lung growth | Symptoms may overlap other lung illness | A neoplasm may be benign or malignant; symptoms do not establish either | Yes | Assessment and tests; do not equate with confirmed cancer | [NCI definition][nci_neoplasm] |
| Spontaneous pneumothorax | Collapsed lung | Sudden chest pain, breathlessness | Requires urgent assessment, often imaging | Yes | Prompt care; emergency for severe difficulty | [Health NZ][healthnz_pneumothorax] |
| Tuberculosis | Tuberculosis / TB; kifua kikuu | Persistent cough, fever, night sweats, weight loss | Symptoms do not confirm TB; overlap/co-infection possible | Yes | Facility/TB testing for cough at least two weeks or concerning associated signs | [Kenya community guideline pp.124-125][ke_community_2024] |
| URTI | Nose or throat infection | Runny/blocked nose, cough, sore throat | Broad category, not a pathogen or synonym for influenza | Yes | Explain uncertainty; assess warning signs/persistence | [NHS RTIs][nhs_rti] |
| Viral pharyngitis | Viral sore throat | Sore throat, pain swallowing | Bacterial and other causes overlap | Yes | Explain possible cause; assess swallowing/breathing difficulty | [Kenya hospital guideline 24.1.2][ke_hospitals_2024] |
| Whooping cough | Whooping cough / pertussis; kifaduro | Coughing fits; babies may stop breathing without whoop | Early cold-like illness; needs clinical assessment | Yes | Prompt assessment, especially infants; emergency for breathing pauses | [NHS inform pertussis][nhs_pertussis] |
| Flu-like respiratory symptom pattern | Flu-like symptoms; cause uncertain | Fever, cough, sore throat, aches | Influenza, COVID-19, other viruses, pneumonia; severity matters | No separate syndrome class | Use explanatory wording; never convert to confirmed influenza | [WHO ILI][who_ili], [CDC][cdc_flu_covid] |
| Malaria / undifferentiated fever | Fever needing assessment | Fever, chills, headache; sometimes aches | Exposure/geography matter; symptoms overlap respiratory illness | **No** | Clinician assessment and parasitological testing when indicated; no automatic antimalarial advice | [Kenya malaria 2025][ke_malaria_2025], [WHO malaria][who_malaria] |
| COVID-19 | COVID-19 | Cough, fever, sore throat, tiredness | Cannot reliably distinguish from influenza by symptoms | **No** active V3 class; legacy synthetic V2 extension only | State scope limitation; consider testing/assessment | [CDC][cdc_flu_covid] |
| HIV-associated illness | Assessment/testing when indicated | Variable; fever, cough, weight loss may occur | Symptoms cannot determine HIV status; TB and other infections may coexist | **No** | Appropriate confidential testing/clinical care, not a symptom-based HIV label | [WHO HIV][who_hiv] |
| Allergic rhinitis | Nasal allergy | Sneezing, itchy/runny nose | Not identical to the source class allergic sinusitis | **No** active V3 class; legacy synthetic V2 extension only | Assess allergy and alternatives; do not silently merge labels | [WHO asthma/allergic associations][who_asthma], [NHS sinusitis][nhs_sinusitis] |
| Headache and tiredness alone | Symptoms need more information | Headache, fatigue | Respiratory model cannot establish cause or exclude serious illness | Symptoms may be features; no validated general differential | Ask duration/severity and relevant symptoms; assess persistence/worsening or warning signs | [Kenya community headache section][ke_community_2024], [WHO malaria][who_malaria] |

## Small, explicit safety refinements

These sources support escalation wording, not a comprehensive validated triage algorithm. An absence of recognized flags must not be presented as “safe”, “mild”, or “serious illness ruled out”. Keep immediate care advice ahead of all model follow-up questions.

* **Respiratory danger:** severe difficulty breathing, gasping/inability to speak, blue/grey lips, breathing pauses or a child difficult to wake warrant emergency care. New breathing trouble, chest pain or coughing blood requires prompt clinical assessment. Keep severity distinctions where the input supports them; do not suggest an isolated mild symptom proves an emergency. [NHS bronchitis][nhs_bronchitis], [NHS bronchiolitis][nhs_bronchiolitis].
* **Headache with warning signs:** fever/headache with neck stiffness or confusion should trigger urgent assessment rather than a respiratory prediction. Do not require every classic meningitis sign: NICE explicitly says clinical suspicion remains possible without the full combination. Do not infer meningitis is absent when neck stiffness is denied. [Kenya primary care guideline, section 4.6 p.70][ke_primary_2024], [WHO meningitis][who_meningitis], [NICE NG240][nice_meningitis].
* **Sudden unusually severe headache:** an extremely painful headache starting suddenly warrants emergency assessment, independent of a respiratory prediction. The implemented check covers explicit sudden-severe/worst/thunderclap wording, not every dangerous headache presentation. [NHS headache guidance][nhs_headaches].
* **Chest pressure/tightness:** new central pressure/squeezing, particularly with spreading discomfort, breathlessness, sweating or nausea, needs emergency assessment. Do not interpret it automatically as asthma merely because asthma is in the model. Atypical presentations exist. [WHO heart attack][who_heart_attack].
* **Infant fever:** age under three months with measured temperature at least 38°C is high risk and needs urgent clinical assessment; a parent suspecting fever in such a baby should seek advice promptly. Whole-year age `0` spans more than this age range and cannot establish exact months. Ask age in months if necessary, or conservatively refer an infant with fever; never delay care for reported danger signs. [NICE NG143][nice_fever], [NHS child fever][nhs_fever].
* **Prolonged cough:** Kenya's community guideline says cough **two weeks or more**, so exactly 14 days belongs in a referral consideration, not only `>14`. A response bucket “3 to 14 days” does not prove the cough lasted 14 days; use exact duration if supplied or clarify instead. This is assessment advice, not an automatic TB diagnosis. [Kenya community guideline p.124][ke_community_2024].

Suggested calm scope wording: “Headache and tiredness can have several causes. This respiratory symptom tool cannot identify the cause from these symptoms alone. Tell a healthcare professional if symptoms persist or worsen. Seek urgent care for a severe headache with neck stiffness, confusion or other serious symptoms.” This is draft communication, not a clinically reviewed expected diagnosis for a test set.

Suggested respiratory overlap wording: “Fever, cough, sore throat and aches can occur with several respiratory infections. These symptoms do not confirm influenza, and this model does not assess every possible cause. A healthcare professional can advise whether examination or testing is needed.” Do not infer viral aetiology from the symptom count alone.

## Terminology maintenance and review

The new dictionary keeps class IDs stable. `Larygospasm` is corrected only for presentation. “Pulmonary neoplasm” stays an abnormal growth with both malignant and non-malignant possibilities; it is neither silently softened into a benign diagnosis nor relabelled confirmed cancer. Combined asthma/bronchospasm and COPD/infection labels remain combined rather than inventing specificity. Rare/technical terms retain their medical name and receive a short explanation. No medicines/doses are embedded in terminology.

Schema version 1 stores `conditions[exact_model_class]` with `medical_name`, `display_name.en/sw`, `description.en/sw`, and `source_ids`. Optional terminology notes preserve known ambiguities. Add a source and reviewed wording without rewriting prediction logic; adding a dictionary entry must never be taken as authorization to add a trained class. A model-class coverage check should compare against the active bundle. Keep this resource distinct from editable legacy condition information.

Before patient use, commission Kenyan clinician review of class definitions, escalation specificity and missing alternatives; professional Kiswahili review and comprehension testing; and prospective local external validation across ages, pregnancy, HIV/immunosuppression, care settings and regions. Obtain real encounter data with documented diagnostic standards, temporal/site-separated evaluation, consent/governance and follow-up. Include out-of-scope and mixed illnesses. Assess calibration, abstention coverage/selective accuracy, missed urgent cases and subgroup errors with uncertainty intervals. Recalibration on simulated records alone cannot demonstrate clinical calibration. Adding malaria/COVID/HIV requires adequate training labels, a justified scope and independent validation, not a naming change.

The current national lung programme lists 2026 integrated TB/lung guidance and 2025 chronic respiratory guidance. Its linked PDFs timed out or exceeded the web reader size limit in this research run, so no detailed recommendation is attributed to unread text. Accessible 2024 national guideline passages above were used for the documented decisions. A Kenyan reviewer should reconcile these with the newer programme guidance before deployment. [Kenya NTLD-P resource listing][ke_lung_programme].

## References and what each supports

Links were retrieved through web search/open during this research. The source registry in the dictionary is the machine-readable subset supporting condition explanations. Additional references here support scope and safety. Foreign emergency phone numbers and UK referral pathways were not transplanted into the Kenyan UI.

* [Kenya MOH community clinical guidelines (2024)][ke_community_2024]: TB assessment at cough >=2 weeks, associated signs; persistent severe headache assessment.
* [Kenya MOH primary care clinical guidelines (2024)][ke_primary_2024]: section 4.6 meningitis/encephalitis warning features.
* [Kenya MOH hospital clinical guidelines (2024)][ke_hospitals_2024]: section 24.1 upper respiratory categories and sore throat causes.
* [Kenya malaria guideline, seventh edition revised 2025][ke_malaria_2025]: parasitological testing before malaria treatment; no symptom-only malaria assignment.
* [Kenya NTLD-P patient management resources][ke_lung_programme]: local TB/asthma/chronic lung programme and newer guideline availability; linked full text not used.
* [WHO influenza][who_influenza], [WHO ILI definitions][who_ili], [CDC flu/COVID][cdc_flu_covid], [CDC flu diagnosis][cdc_flu_testing]: pathogen versus syndrome, overlap and confirmation limits.
* [WHO malaria][who_malaria], [WHO HIV][who_hiv]: missing differential scope and testing rather than inferred diagnosis.
* [WHO asthma][who_asthma], [WHO COPD][who_copd], [WHO pneumonia][who_pneumonia]: accurate short disease explanations, respiratory severity and overlapping symptoms.
* [NHS laryngitis][nhs_laryngitis], [sinusitis][nhs_sinusitis], [bronchiectasis][nhs_bronchiectasis], [bronchiolitis][nhs_bronchiolitis], [bronchitis][nhs_bronchitis], [croup][nhs_croup], [epiglottitis][nhs_epiglottitis], [pertussis][nhs_pertussis], [RTIs][nhs_rti]: patient-facing condition descriptions and warning-sign examples.
* [Mayo laryngospasm][mayo_laryngospasm], [NCI neoplasm][nci_neoplasm], [NHLBI breathing failure causes][nhlbi_respiratory_failure], [Health NZ collapsed lung][healthnz_pneumothorax]: less familiar labels without false reassurance or changed medical meaning.
* [WHO meningitis][who_meningitis], [NICE NG240][nice_meningitis], [WHO heart attack][who_heart_attack], [NICE NG143][nice_fever], [NHS fever][nhs_fever]: targeted non-respiratory and infant warning signs; these do not validate a rule engine.
* [NHS headaches][nhs_headaches]: sudden extremely painful headache as an emergency warning; no headache diagnosis is assigned.

[ke_community_2024]: https://health.go.ke/sites/default/files/2025-04/Clinical%20Guidelines%20for%20Level%201%20Community%20Health%20Services.pdf
[ke_primary_2024]: https://health.go.ke/sites/default/files/2025-04/Clinical%20Guidelines%20for%20Level%202%20Dispensaries%20Medical%20Clinics%20Level%203%20Health%20Centres%20Nursing.pdf
[ke_hospitals_2024]: https://health.go.ke/sites/default/files/2025-04/Clinical%20Guidelines%20for%20Management%20Level%204%20Primary%20Care%20Hospitals%20Level%205%20Secondary%20Hospitals%20Level%206%20Tertiary%20Hospitals%20%E2%80%93%20National%20Hospitals.pdf
[ke_malaria_2025]: https://osp.nckenya.go.ke/media/uploads/1765287097AFT_REVISED_MALARIA_GUIDELINES_7TH_EDITION.pdf
[ke_lung_programme]: https://nltp.co.ke/patient-management/
[who_influenza]: https://www.who.int/news-room/fact-sheets/detail/influenza-(seasonal)
[who_ili]: https://www.who.int/teams/global-influenza-programme/surveillance-and-monitoring
[cdc_flu_covid]: https://www.cdc.gov/flu/about/flu-vs-covid19.html
[cdc_flu_testing]: https://www.cdc.gov/flu/testing/
[who_malaria]: https://www.who.int/news-room/fact-sheets/detail/malaria
[who_hiv]: https://www.who.int/news-room/fact-sheets/detail/hiv-aids
[who_copd]: https://www.who.int/news-room/fact-sheets/detail/chronic-obstructive-pulmonary-disease-(copd)
[who_asthma]: https://www.who.int/news-room/fact-sheets/detail/asthma
[who_pneumonia]: https://www.who.int/news-room/fact-sheets/detail/pneumonia
[nhs_laryngitis]: https://www.nhs.uk/conditions/laryngitis/
[nhs_sinusitis]: https://www.nhs.uk/conditions/sinusitis-sinus-infection/
[nhs_bronchiectasis]: https://www.nhsinform.scot/illnesses-and-conditions/lungs-and-airways/bronchiectasis
[nhs_bronchiolitis]: https://www.nhs.uk/conditions/bronchiolitis/
[nhs_bronchitis]: https://www.nhs.uk/conditions/bronchitis/
[nhs_croup]: https://www.nhs.uk/conditions/croup/
[nhs_epiglottitis]: https://www.nhs.uk/conditions/epiglottitis/
[nhs_pertussis]: https://www.nhsinform.scot/illnesses-and-conditions/infections-and-poisoning/whooping-cough
[nhs_rti]: https://www.nhs.uk/conditions/respiratory-tract-infection/
[mayo_laryngospasm]: https://www.mayoclinic.org/diseases-conditions/gerd/expert-answers/laryngospasm/faq-20058269
[nci_neoplasm]: https://www.cancer.gov/publications/dictionaries/cancer-terms/def/tumor
[nhlbi_respiratory_failure]: https://www.nhlbi.nih.gov/health/respiratory-failure/causes
[healthnz_pneumothorax]: https://www.healthnz.govt.nz/health-topics/conditions-treatments/lungs/collapsed-lung-pneumothorax
[who_meningitis]: https://www.who.int/news-room/fact-sheets/detail/meningitis
[nice_meningitis]: https://www.nice.org.uk/guidance/ng240/chapter/Recommendations
[who_heart_attack]: https://www.who.int/news-room/fact-sheets/detail/heart-attack
[nice_fever]: https://www.nice.org.uk/guidance/NG143/chapter/recommendations
[nhs_fever]: https://www.nhs.uk/symptoms/fever-in-children/
[nhs_headaches]: https://www.nhs.uk/symptoms/headaches/
