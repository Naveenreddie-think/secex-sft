\# Findings — SecEx-SFT



\## Dataset Construction



\- 200 real security advisories pulled from the GitHub Advisory Database (GHSA) via GraphQL API.

\- Structured fields (`severity`, `cwe\_category`, `affected\_products`) were mapped directly from GHSA's structured metadata — reliable, \~100% CWE coverage across the sample.

\- `attack\_vector` was initially parsed from CVSS vector strings, but only 76% of advisories had one. For the remaining \~24%, defaulted to `unknown` even when the advisory prose stated the attack vector explicitly (e.g. "a network attacker can..."). This was corrected by hand during review wherever the text made it clear — a real limitation of relying on structured CVSS fields alone.

\- `impact\_summary` and `remediation\_action` are not reliably present as structured GHSA fields — they had to be derived from free-text advisory descriptions.



\## Label Drafting: Local LLM as a Labeling Assistant



\- Used a locally-hosted Qwen2.5-3B-Instruct (via Ollama) to draft `impact\_summary` and `remediation\_action` for all 200 items from the raw advisory text, rather than writing these fields from scratch by hand.

\- 198/200 drafts succeeded; 2/200 failed due to the small model's unreliable JSON formatting (missing key in one case, malformed JSON in the other). Both were left with placeholder text and require hand-correction if reused later.

\- Spot-checking drafts against source text showed the local 3B model was generally accurate and usable as a first draft, but occasionally introduced plausible-sounding details not actually stated in the source advisory (a hallucination pattern typical of smaller models) — e.g., one SSRF advisory's draft added "credential theft and internal network scanning" as consequences, which the source text never mentioned.



\## Known Limitation: Review Pass Did Not Catch All Ungrounded Details



\- All 200 items were hand-reviewed for structural correctness (severity, attack vector, CWE, affected products) and for general summary quality.

\- However, a full sentence-by-sentence grounding check against source text was not performed on every one of the 200 items given time constraints. At least one confirmed case (`GHSA-8q49-2h5h-434x`) retained a hallucinated detail in `impact\_summary` that was identified during spot-checking but not corrected in the final dataset.

\- \*\*This is a known, documented limitation of the current dataset, not a silent gap.\*\* The dataset should not be treated as 100% hallucination-free at the field level. Future work: a dedicated grounding-check pass (potentially automated — checking whether summary claims have lexical/semantic overlap with source text) before using this dataset for anything beyond this portfolio project.



\## Vendor/Ecosystem Field Note



\- GHSA organizes advisories by package ecosystem (`GO`, `NPM`, `PIP`, etc.), not by CPE-style vendor/product convention used by NVD. The `vendor` field in this dataset reflects ecosystem, not an actual maintainer/vendor name — a known simplification stemming from the data source, not an extraction error.



\## Baseline Evaluation (Prompting-Only, Unmodified Qwen2.5-3B-Instruct)



One-shot prompting, temperature=0 for reproducibility, evaluated with a shared harness against both an in-distribution test set and a fully out-of-distribution test set (entire "Uncontrolled Resource Consumption" CWE category held out from training/dev entirely).



| Metric | ID test (n=19) | OOD test (n=16) |

|---|---|---|

| Schema-valid rate | 89.5% | 75.0% |

| Severity accuracy | 35.3% | 75.0% |

| Attack vector accuracy | 58.8% | 50.0% |

| CWE category (fuzzy match, threshold 0.5) | 23.5% | 16.7% |

| CVE ID exact match | 47.1% | 33.3% |



\*\*Notable failure mode\*\*: the dominant cause of schema-invalid output was the base model producing `attack\_vector: "remote"` instead of the schema's required `"network"` enum value — a vocabulary mismatch (CVSS/common-parlance terminology vs. the project's exact schema), not a conceptual extraction error. This is expected to be one of the more directly fixable gaps via fine-tuning, since SFT should teach the model the exact schema vocabulary.



\*\*Eval harness bug caught and fixed during this step\*\*: an early version of the scoring harness compared Python `Enum` members using `str()`, which returns `"ClassName.member\_name"` rather than the actual string value for a custom `(str, Enum)` mixin — this silently zeroed out `severity` and `attack\_vector` accuracy entirely before being caught and fixed (`.value` used explicitly instead). Worth noting as a reminder that eval harness correctness needs the same scrutiny as model behavior — a scoring bug can otherwise silently invalidate every downstream comparison, including making a fine-tuned model look artificially better if its outputs happen not to trigger the same bug.



\*\*Interpretation caution\*\*: severity accuracy is counterintuitively higher on the OOD set (75% vs 35.3% ID) — this is noted rather than explained, given the small OOD sample size (16 items); it should not be treated as a proven mechanism without further investigation once more data/results are available.

## QLoRA Fine-Tuning Results: The Core Finding

Trained via Unsloth (LoRA rank=16, alpha=16, 4-bit base, targeting all attention + MLP projection layers) on Qwen2.5-3B-Instruct, 146 training examples, 3 epochs. Train loss: 2.2 → 1.47 average. Eval loss: 1.428 → 1.369 → 1.360 across epochs (still decreasing at epoch 3, no overfitting signature observed within this budget).

| Metric | Baseline ID | Fine-tuned ID | Baseline OOD | Fine-tuned OOD |
|---|---|---|---|---|
| Schema-valid rate | 89.5% | 100% | 75.0% | 100% |
| Severity accuracy | 35.3% | 36.8% | 75.0% | 50.0% |
| Attack vector accuracy | 58.8% | 63.2% | 50.0% | 68.8% |
| CWE category (fuzzy match) | 23.5% | 47.4% | 16.7% | **0.0%** |
| CVE ID exact match | 47.1% | 42.1% | 33.3% | 31.3% |

**Clean win — schema compliance**: fine-tuning eliminated 100% of the enum-vocabulary mismatch failures (`"remote"` vs `"network"`) that caused ~10-25% of baseline outputs to fail schema validation. Both test sets hit 100% schema-valid post-SFT.

**Clean win — in-distribution CWE categorization**: fuzzy-match CWE accuracy nearly doubled on the in-distribution test set (23.5% → 47.4%), suggesting the model learned the project's specific CWE-naming conventions well for categories it saw during training.

**Critical negative finding — CWE categorization does not generalize to a novel category**: on the out-of-distribution test set (an entire CWE category, "Uncontrolled Resource Consumption," held out from training), CWE accuracy dropped from 16.7% (baseline) to **0%** (fine-tuned). This is the most important result in this project. The likely mechanism, offered as a hypothesis rather than a proven fact: fine-tuning on many in-distribution categories taught the model a confident, specific mapping from vulnerability-description patterns to known category names, but this specialization did not transfer to a genuinely unseen category — if anything, the model's increased confidence in learned patterns actively hurt its ability to produce a correct answer for something outside that learned distribution, where the untrained base model's more general (if fuzzier) knowledge occasionally succeeded by chance.

**Secondary regression — severity accuracy also dropped on OOD** (75% → 50%), consistent with the same generalization gap, though the small OOD sample size (n=16) means this shouldn't be over-interpreted in isolation.

**CVE ID accuracy declined slightly on both splits** (47.1%→42.1% ID, 33.3%→31.3% OOD). Given only 10% of the original 200 examples had a real CVE ID, the training data's heavy `null` class imbalance is a plausible cause — the model may have learned to default toward `null` more confidently post-SFT. Not deeply investigated further given time constraints; flagged as an open question rather than a resolved explanation.

**Overall interpretation**: QLoRA fine-tuning on this small (146-example) dataset delivered a genuine, substantial improvement on tasks close to the training distribution — perfect schema compliance and much better in-distribution CWE categorization — but did not deliver, and may have actively hurt, generalization to a genuinely novel vulnerability category. This is a realistic and honest picture of what small-scale QLoRA fine-tuning can and cannot do, and is arguably a more useful result for demonstrating real engineering judgment than a uniformly positive outcome would have been.

## Serving-Time Observation: Hallucination on Underspecified Input

When tested with a synthetic advisory that deliberately omitted any specific CVE ID, vendor, or product name, the merged fine-tuned model still produced a fully populated, plausible-looking `affected_products` entry and a fabricated CVE ID rather than returning `null`/empty for the missing fields. This did not surface during formal evaluation because every real GHSA advisory in the dataset contains an explicit package/product reference, so the model was never trained on genuinely ambiguous input. This is a known, documented limitation of the current model: it is not guaranteed to abstain when identifying details are absent from the source text, and outputs should not be treated as grounded by default when tested on inputs unlike the training distribution.

## Hallucination Mitigation: Prompting Alone Was Insufficient

Tested two mitigation layers against the underspecified-input hallucination described above:

1. **Stronger system prompt** explicitly instructing the model never to invent CVE IDs, vendor names, or product names not literally present in the source text. Result: **ineffective** — the model still fabricated a plausible-looking CVE ID and package name on the same test case, just with different specific (wrong) values than before.
2. **Code-level groundedness check**, implemented as a post-processing step that verifies any specific `cve_id` or `affected_products.product` value literally appears (normalized) in the source text before allowing it through; ungrounded values are nulled/dropped rather than trusted. Result: **effective** — correctly caught and removed both fabricated values in testing.

This is a concrete example of a broader, important lesson: prompt-level instructions are not a reliable safety mechanism for output correctness in a small fine-tuned model. A verifiable, code-level check against the actual source text is required wherever hallucination risk matters — the model's own stated intent ("I won't invent things") cannot be trusted at face value.

## Groundedness Check Extended to version_range

Live testing with a fresh, out-of-training advisory (Discourse Subscriptions authorization bypass) surfaced a gap in the original groundedness check: it verified `cve_id` and `affected_products.product` but not `version_range`. The model fabricated a specific version number ("<= 4.1.0") that did not appear anywhere in the source text, which the original check let through since it only validated product name and CVE ID. Extended the check to validate `version_range` against the source text as well; confirmed the fix correctly nulls fabricated version numbers on retest while leaving genuinely-stated details (CVE ID, product name) untouched.

This is a useful illustration of hallucination as a per-field problem, not a per-extraction problem — a model can be correctly grounded on some fields of an output and fabricate others in the same response, so groundedness verification needs to cover every field capable of carrying a specific, checkable claim, not just the most obviously risky one.

## Groundedness Gap: Fabricated Entities Leaking Into Free-Text Fields

Live testing surfaced a real gap in the groundedness check: it validated cve_id, product name, and version_range as structured fields, but did not check whether the same fabricated entity also appeared in the free-text impact_summary or remediation_action fields. In one case, the model fabricated a product name ("@microsoft/fast-api-authentication"), which was correctly caught and dropped from affected_products — but the same fabricated name still appeared, unflagged, in the remediation_action text. This meant the UI displayed a "details removed" notice while simultaneously showing that same unverified detail elsewhere on the page, which is arguably worse than no check at all since it implies the output was fully cleaned when it wasn't.

Fixed by scanning free-text fields for any entity already identified as ungrounded from the structured-field check, and surfacing a warning if found. Chose to flag rather than auto-strip the substring from prose, since removing a mid-sentence phrase programmatically often produces broken grammar — transparency about the remaining issue was judged preferable to a silent, potentially malformed edit.


## CVE ID Regression: Root Cause Identified

The unexplained CVE ID accuracy regression (47.1%→42.1% ID, 33.3%→31.3% OOD) was investigated by categorizing every fine-tuned prediction into correct / missed (gold has a CVE, model predicted null) / hallucinated (gold is null, model invented one) / wrong (both non-null, different values).

**id_test (n=19)**: 8 correct, 10 missed, 0 hallucinated, 1 wrong.
**ood_test (n=16)**: 5 correct, 11 missed, 0 hallucinated, 0 wrong.

Across both splits, the fine-tuned model's CVE ID errors are almost entirely (30 of 31 total errors) a single failure mode: **defaulting to null when a real CVE ID exists in the source text.** It essentially never fabricates or confuses CVE IDs.

This confirms the training-data-imbalance hypothesis: only ~10% of the 200 training examples contained a real CVE ID (GHSA-native advisories frequently lack one). Fine-tuning strengthened the model's prior toward predicting null, trading recall on the minority case (real CVE present) for consistency — a precision/recall trade-off, not a hallucination problem, and notably the opposite failure mode from the free-text hallucination issues found elsewhere in this project.

**This is a data problem, not a model or method problem.** The fix would be oversampling or upweighting the ~20 training examples containing a real CVE ID, not changing the training approach itself. Not implemented in this iteration given time constraints, but the mechanism is now understood and documented rather than left as an open question.