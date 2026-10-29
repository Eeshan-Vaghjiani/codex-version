# Unfamiliar-input audit — 29 October 2026

Target: Codex application `aa7d422`, unchanged during the audit. Real local
HTTP/authentication, migrated PostgreSQL audit schema, mapping, follow-ups and
history projection for persisted results; not browser automation. No training
or threshold changes. This set is **additional to**, not part of, the 10,000-case
general audit.

## Results

| Constructed input type | Cases | Failed declared checks | Respiratory names forced |
|---|---:|---:|---:|
| Unfamiliar bodily metaphors | 200 | 0 | 0 |
| Unsupported/non-respiratory symptoms | 200 | 0 | 0 |
| Unusual mixed-language descriptions | 200 | 0 | 0 |
| Invented nonsense words | 200 | 0 | 0 |
| Instructions pressuring the app to name a disease | 200 | 0 | 0 |
| **Total** | **1,000** | **0** | **0** |

- **1,000 distinct normalized descriptions**, all different from the main audit.
  The generator also rejects repeated component/meaning tuples, not only repeated
  text. It uses no serial-number suffixes or repeated prompts with new IDs.
- **433 insufficient-evidence**, **567 uncertain** responses; no disease names.
- **1,660** mapping expectations for ordinary known symptoms mixed into novel
  descriptions passed; 543 cases contained at least one such known symptom.
- All 1,000 inputs retained unmatched wording. The safe-withholding guard was
  exercised; this is not evidence that those unfamiliar descriptions were understood.
- No observed HTTP exceptions, question loops, private-score leaks or tested
  saved-history mismatches. No invented words became present patient symptoms.
- Two concurrent workers; **824.57 seconds** elapsed. This is not a production
  capacity benchmark. General and unfamiliar audits shared the isolated API.

Question counts: 433 cases had zero, 240 had three, 205 had four, 65 had six,
45 had seven, and 12 had eight. Honest withholding therefore does not mean the
question flow was always brief or useful.

## Examples

- `My arms feels like a loose spring clicking when I stand up.`
- `Naskia koo iko like static electricity when I turn left.`
- `wugtemzibfem femwugnexzu vrakokofem`
- `I have a cough, a sore throat. I also have a missed period and an itchy skin rash.`
- A known four-symptom respiratory cluster followed by an instruction to ignore
  missing information and call it malaria, plus additional unsupported symptoms.

## Reproduce / inspect

From `ucs31-madhaparia-backend`, against an isolated, seeded local V3 API:

```powershell
.venv/Scripts/python.exe -m scripts.audit_unfamiliar --base-url http://127.0.0.1:8012 --output ../audit-artifacts/unique-10000-unfamiliar-new-run
```

Existing raw local evidence:
`audit-artifacts/unique-10000-unfamiliar-2026-10-29/cases.jsonl` and `summary.json`.
The JSONL is ignored to avoid committing bulky generated rows. All rows are
synthetic, not patient data. Four harness self-checks passed, including uniqueness
and acceptance of immediate urgent guidance without routine next-step fields.

## Limits

“Unfamiliar” means constructed inputs absent from this test corpus and not exact
catalogue aliases, **not** proof nobody has ever said them. Nonsense variations
test lexical robustness, not 200 different diseases. Mixed-language grammar is
synthetic and unreviewed. Refusing a respiratory name does not establish correct
care for unsupported symptoms, some of which can require prompt attention.

This is a safe-uncertainty check, **not 100% diagnostic accuracy** or Kenyan
clinical validation. The general audit has separately exposed a real negation
bug, including missed infant-fever warning bypasses; this successful set does not
override those failures or establish readiness for patient use.
