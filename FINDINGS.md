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

