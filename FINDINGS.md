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

