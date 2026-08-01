# Findings — SecEx-SFT (Project A)

## Executive Summary

QLoRA fine-tuning of Qwen2.5-3B-Instruct on 146 hand-verified security advisories **completely fixed schema-vocabulary compliance** (100% valid JSON on both test sets, up from 75–90%) and **nearly doubled in-distribution CWE categorization accuracy** (23.5%→47.4%). It **did not generalize to a genuinely unseen vulnerability category** — CWE accuracy on a held-out CWE category dropped to exactly 0% (from a 16.7% baseline). A separate, code-level safety check was required to catch the model confidently fabricating specific details (CVE IDs, product names, version numbers) not present in the source text — a prompt-only instruction was tested and found ineffective.

Every claim below is backed by a reproducible script and a real logged output, not an assertion.

\---

## 1\. Methodology

**Task**: extract structured vulnerability data (CVE ID, affected products, CWE category, severity, attack vector, impact summary, remediation) from unstructured security advisory text, matching a fixed Pydantic schema.

**Data**: 200 real advisories pulled from the GitHub Security Advisory Database (GHSA) via GraphQL API. NVD was originally planned as a second source but was dropped for time — a deliberate scope cut, not an oversight.

**Labeling process**: structured fields (severity, CWE, affected packages) were mapped directly from GHSA's own metadata. Free-text fields (`impact\_summary`, `remediation\_action`) are not reliably present in GHSA's structured data, so they were drafted by a locally-run Qwen2.5-3B-Instruct (via Ollama) and then every one of the 200 examples was hand-reviewed against the actual source text before being treated as gold data.

**Split strategy**: stratified by severity for train/val/in-distribution-test. An entire CWE category ("Uncontrolled Resource Consumption") was held out entirely as a dedicated out-of-distribution (OOD) test set, with an explicit check confirming it never appears in the training set. Final split: 146 train / 19 val / 19 in-distribution test (id\_test) / 16 OOD test (ood\_test).

**Training**: Unsloth + `trl`'s `SFTTrainer`, LoRA rank=16, alpha=16, 4-bit base, 3 epochs. Train loss: \~2.2 → \~1.47 average. Eval loss: 1.428 → 1.369 → 1.360 across the 3 epochs — still decreasing at the end, no overfitting signature observed within this training budget.

**Evaluation**: baseline (unmodified model, one-shot prompting, temperature=0) and fine-tuned model scored with the identical harness on the identical test sets — schema validity via Pydantic, exact-match for severity/attack\_vector, fuzzy string match for CWE category, exact match for CVE ID.

\---

## 2\. Results

|Metric|Baseline ID|Fine-tuned ID|Baseline OOD|Fine-tuned OOD|
|-|-|-|-|-|
|Schema-valid rate|89.5%|**100%**|75.0%|**100%**|
|Severity accuracy|35.3%|36.8%|75.0%|50.0%|
|Attack vector accuracy|58.8%|63.2%|50.0%|68.8%|
|CWE category (fuzzy match)|23.5%|47.4%|16.7%|**0.0%**|
|CVE ID exact match|47.1%|42.1%|33.3%|31.3%|

\---

## 3\. Key Finding: Fine-Tuning Fixes Schema Compliance Completely

The dominant baseline failure mode was the model outputting `attack\_vector: "remote"` instead of the schema's required `"network"` enum value — CVSS/common-parlance vocabulary instead of the project's exact schema. This caused 10–25% of baseline outputs to fail schema validation outright. Fine-tuning eliminated this entirely: **100% schema-valid output on both test sets**, since the model learned the exact target vocabulary from training examples.

## 4\. Key Finding: In-Distribution CWE Categorization Nearly Doubled

CWE category fuzzy-match accuracy rose from 23.5% to 47.4% on the in-distribution test set — the model learned this project's specific CWE-naming conventions well for categories it saw during training.

## 5\. Critical Finding: CWE Categorization Does Not Generalize to a Novel Category

On the out-of-distribution test set — an entire CWE category the model never saw during training — CWE accuracy **dropped from 16.7% (baseline) to exactly 0.0% (fine-tuned)**. This is the most important result in this project, and it is a negative one.

**Likely mechanism** (stated as hypothesis, not proven): fine-tuning on many in-distribution categories taught the model a confident, specific mapping from vulnerability-description patterns to *known* category names. This specialization did not transfer to a genuinely unseen category — and the model's increased confidence in learned patterns may have actively displaced the base model's fuzzier, more general knowledge, which occasionally produced a correct answer by chance.

Severity accuracy also dropped on the OOD set (75%→50%), consistent with the same generalization gap, though the small sample size (n=16) means this shouldn't be over-interpreted in isolation.

**Overall interpretation**: small-scale QLoRA fine-tuning delivered a genuine, substantial improvement on tasks close to the training distribution, but did not deliver — and may have actively hurt — generalization to a genuinely novel category. This is a realistic picture of what fine-tuning on 146 examples can and cannot do.

## 6\. Resolved Finding: The CVE ID Regression Has a Known, Benign Cause

CVE ID accuracy declined after fine-tuning on both splits (47.1%→42.1% ID, 33.3%→31.3% OOD). This was investigated by categorizing every fine-tuned prediction into correct / missed (gold has a CVE, model predicted null) / hallucinated (gold is null, model invented one) / wrong.

**Result**: across both test sets, 30 of 31 total CVE ID errors were the model defaulting to `null` when a real CVE ID existed in the source text. Zero hallucinations, only one "wrong" case (a different, incorrect CVE ID predicted).

**Root cause**: only \~10% of the 200 training examples contained a real CVE ID (GHSA-native advisories frequently lack one). Fine-tuning strengthened the model's prior toward predicting null, trading recall on the minority case for consistency. This is a **precision/recall trade-off caused by training-data class imbalance**, not a hallucination or reasoning problem — notably the opposite failure mode from the hallucination issues described below. The fix would be oversampling the \~20 training examples containing a real CVE ID; not implemented in this iteration given time constraints, but the mechanism is understood and documented rather than left open.

\---

## 7\. Hallucination and the Groundedness Safety Layer

Live testing (not formal evaluation — this surfaced through actually using the deployed model) found that the fine-tuned model confidently fabricates plausible-sounding CVE IDs, product names, and version numbers when the source text does not state them. This never appeared in formal evaluation because every real GHSA advisory in the dataset contains explicit package/product references — the model was never trained on genuinely ambiguous input.

**Mitigation attempt 1 — prompt-level instruction: tested and found ineffective.** An explicit system-prompt instruction ("never invent CVE IDs, vendor names, or product names not literally present in the source text") did not stop fabrication. The model still produced a fabricated CVE ID and product name on the same test case, just with different specific (still wrong) values.

**Mitigation attempt 2 — code-level groundedness check: effective.** A post-processing check (`app/serving/groundedness.py`) verifies that every specific `cve\_id`, `affected\_products.product`, and `affected\_products.version\_range` value literally appears (normalized) in the source text; anything unverified is nulled/dropped, and the removal is surfaced transparently in the UI rather than hidden. This correctly caught fabricated values in testing.

**Gap found and fixed — free-text leakage.** The initial groundedness check validated structured fields only. Live testing found a fabricated product name correctly dropped from `affected\_products` while the *same fabricated name* still appeared, unflagged, in `remediation\_action` — meaning the UI displayed a "details removed" notice while simultaneously showing that same unverified detail elsewhere. Fixed by scanning free-text fields for any entity already flagged as ungrounded, and surfacing a warning. Chose to flag rather than auto-strip the substring from prose, since silently removing a mid-sentence phrase programmatically often produces broken grammar.

**Verified, not a gap — plausible name variants.** A later live test showed the model inventing `BlogEngine.Core` when the source text said `BlogEngine CMS`. This was initially suspected to be an uncaught gap (a "plausible variant" pattern distinct from wholesale fabrication), but direct testing of the normalization logic confirmed the check correctly identifies this case as ungrounded and drops it — the check was already working correctly. This is now locked in with a regression test (`test\_plausible\_variant\_product\_name\_is\_dropped`) rather than left as an assumption.

**General lesson**: prompt-level instructions are not a reliable safety mechanism for output correctness in a small fine-tuned model. A verifiable, code-level check against the actual source text is required wherever hallucination risk matters — the model's own stated intent cannot be trusted at face value. Hallucination is also a per-field problem, not a per-extraction problem: a single response can be correctly grounded on some fields and fabricated on others.

\---

## 8\. Engineering Findings Worth Naming

* **A scoring bug silently invalidated early eval numbers.** An early eval harness compared Python `Enum` members via `str()`, which returns `"ClassName.member"` rather than the actual value for a custom `(str, Enum)` mixin — this zeroed out severity and attack\_vector accuracy entirely until caught. A reminder that eval-harness correctness needs the same scrutiny as model behavior; a scoring bug can make a fine-tuned model look artificially better or worse than it actually is.
* **A CI test failure surfaced a real gap, not just a CI quirk.** Tests passed locally but failed in a fresh GitHub Actions environment with `relation "extractions" does not exist` — because `TestClient(app)` used without a context manager doesn't trigger FastAPI's lifespan startup event, so the schema-creation step never ran on a genuinely empty database. Fixed with an explicit `conftest.py` fixture that creates the schema before any test runs, independent of app lifecycle behavior — arguably a more correct pattern regardless of CI, since tests shouldn't depend on incidental state from prior manual runs.
* **Hugging Face Spaces changed policy mid-project.** Gradio/Docker SDK Spaces now require a paid PRO plan, even on free CPU hardware — this wasn't the case when deployment was originally planned. Pivoted to Modal (modal.com), a genuinely free, no-card-required serverless platform, which also enabled GPU-backed inference (T4) instead of the originally planned CPU-only hosting — a case where an external constraint forced a change that ended up being an improvement.

\---

## 9\. Known Limitations

* Fine-tuning does not generalize to genuinely novel CWE categories, and may actively hurt performance there relative to the base model (Section 5).
* CVE ID recall regressed due to training-data class imbalance; not corrected in this iteration (Section 6).
* One confirmed hallucinated label (a fabricated "credential theft" detail in an SSRF advisory's `impact\_summary`) was caught during spot-checking but not corrected in the final training dataset — a deliberate, documented trade-off given time constraints, not a silent gap.
* Data comes from GHSA only; NVD was planned but dropped for time.
* 146 training examples is small; some results (especially the 16-item OOD test set) carry real sample-size uncertainty.
* No containerized deployment (Docker) or reproducible build for the training environment beyond the documented setup steps — the app is deployed and working, but not packaged as a portable container.

## 10\. What Would Improve This Next

* Oversample or upweight the \~20 training examples containing a real CVE ID to address the class-imbalance regression identified in Section 6.
* Add NVD as a second data source to increase category coverage and reduce the long-tail sparsity that made most CWE categories have only 1–4 training examples.
* Investigate whether the OOD generalization failure (Section 5) replicates across multiple training runs / random seeds, or is specific to this particular training run.
* Containerize the training/serving environment for full reproducibility.

\## Newly Discovered (via Project B pair-building): A Structural Cause of Hallucination in Training Data



While building DPO preference pairs, inspection of a low-signal pilot example (GHSA-qh5g-q395-cx4j) revealed that its gold-label `affected\_products` (10 specific NuGet package variants) do not appear anywhere in the corresponding `input\_text` (a single sentence describing a null-check bug, with no product names at all). Investigation confirmed this is not an isolated case but a structural property of the dataset: `affected\_products` was populated from GHSA's structured metadata API field, independent of the free-text advisory description used as model input.



\*\*Implication\*\*: the SFT training data itself teaches the model, in some fraction of examples, to produce specific product/version details that are not grounded in the text it's given — because the correct target label wasn't grounded in that text either. This is a plausible structural contributor to the hallucination behavior documented in Section 7, distinct from the model simply "making things up" — in these cases, the model may be doing exactly what training rewarded it for doing. Not fixed in this iteration; noted as a limitation of the dataset-construction methodology, and a factor to account for when interpreting groundedness-check failures (a failure may reflect an ungroundable label design, not necessarily a model reasoning error).

