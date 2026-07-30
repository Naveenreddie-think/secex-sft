SecEx-SFT



QLoRA fine-tuning of Qwen2.5-3B-Instruct for structured vulnerability extraction from unstructured security advisory text — with a full-stack review pipeline, a rigorous before/after evaluation, and a groundedness safety layer that catches the model's own hallucinations before they reach a user.



Security advisories (CVE descriptions, GitHub Security Advisories, vendor bulletins) are published as free-form prose. Downstream tooling — SOC dashboards, patch-prioritization systems, SIEM ingestion — needs this as structured, schema-valid JSON. This project asks a specific, testable question: can QLoRA fine-tuning on a small, hand-verified dataset measurably improve structured extraction quality on the same base model, and does that improvement actually generalize to a genuinely unseen vulnerability category?



The honest answer, backed by a real held-out experiment, is: yes and no — and that "no" is the most important result in this repo.



Live demo



\## Live demo



\- \*\*Extraction tool\*\*: https://secex-frontend.onrender.com/extract.html

\- \*\*Label review tool\*\*: https://secex-frontend.onrender.com/review.html

\- \*\*Backend API\*\*: https://secex-sft.onrender.com



Note: the backend is on Render's free tier and may take 30-60s to wake up if idle. Model inference runs on a Modal-hosted GPU endpoint and also has a cold-start delay (10-30s) after periods of inactivity — the first extraction after a lull will be slower than subsequent ones.



The headline result



Trained via Unsloth (LoRA r=16, 4-bit base, 3 epochs, 146 hand-verified training examples), evaluated with a shared scoring harness against two held-out test sets: an in-distribution set, and a fully out-of-distribution set built by holding out an entire CWE category from training.



Metric	Baseline (prompting only) — ID	Fine-tuned — ID	Baseline — OOD	Fine-tuned — OOD

Schema-valid rate	89.5%	100%	75.0%	100%

Severity accuracy	35.3%	36.8%	75.0%	50.0%

Attack vector accuracy	58.8%	63.2%	50.0%	68.8%

CWE category (fuzzy match)	23.5%	47.4%	16.7%	0.0%

CVE ID exact match	47.1%	42.1%	33.3%	31.3%



Fine-tuning completely fixed schema-vocabulary compliance (both test sets hit 100% valid JSON, up from 75-90%) and nearly doubled in-distribution CWE categorization accuracy.



Fine-tuning did not generalize to an unseen category — CWE accuracy on the held-out category dropped to exactly 0%, down from 16.7% at baseline. The likely mechanism: specializing on many in-distribution categories taught the model a confident, specific mapping to known category names, which didn't transfer to a genuinely novel one — and may have actively displaced the base model's fuzzier, more general knowledge that occasionally got it right by chance.



Full methodology, every intermediate finding, and the reasoning behind each design decision is in FINDINGS.md.



Why this project holds up under questioning



Every claim above is backed by a real, reproducible artifact, not an assertion:



Stratified train/val/test split with an entire CWE category held out — verified via an explicit leakage check that the held-out category never appears in training

Reproducible baseline (temperature=0, one-shot prompting) evaluated with the exact same scoring harness used for the fine-tuned model, on the exact same test sets

A scoring bug was caught and fixed mid-evaluation — an early version of the harness silently zeroed out two metrics due to Python enum serialization; documented in FINDINGS.md as a reminder that eval code needs the same scrutiny as model behavior

A live, verified safety layer: the model hallucinates specific details (CVE IDs, product names, version numbers) when the source text doesn't state them. A code-level groundedness check — not just a prompt instruction, which was tested and found insufficient — verifies every specific claim against the actual source text before it reaches the user, and was caught missing a leakage path into free-text fields during live testing, then fixed and re-verified

Architecture

GHSA GraphQL API

&#x20;     │

&#x20;     ▼

Data pipeline (fetch → map to schema → load to Postgres)

&#x20;     │

&#x20;     ▼

Full-stack review tool (FastAPI + Postgres + HTML/JS)

&#x20; — hand-verification of 200 advisories, including

&#x20;   LLM-drafted labels (local Qwen2.5-3B via Ollama)

&#x20;   as a reviewed starting point, not ground truth

&#x20;     │

&#x20;     ▼

Stratified split → baseline eval → QLoRA training (Unsloth)

&#x20;     │

&#x20;     ▼

Adapter merge → /extract endpoint (FastAPI, model preloaded at startup)

&#x20;     │

&#x20;     ▼

Groundedness check (code-level, not prompt-level)

&#x20;     │

&#x20;     ▼

Live extraction UI (paste advisory → structured, verified JSON)

Tech stack

Model: Qwen2.5-3B-Instruct, QLoRA fine-tuned via Unsloth + trl's SFTTrainer

Backend: FastAPI, SQLAlchemy, Postgres (Dockerized for local dev)

Frontend: vanilla HTML/CSS/JS (no framework) — a review tool and a live extraction interface

Data: GitHub Security Advisories (GHSA) via GraphQL API

Eval: custom harness — schema validation (Pydantic), categorical field accuracy, fuzzy-match scoring for free-text categories

Features

1\. Full-stack label review tool



Every one of the 200 training examples was hand-verified, not auto-labeled and trusted. A locally-run Qwen2.5-3B (via Ollama) drafted candidate impact\_summary/remediation\_action text as a starting point; every draft was then reviewed against the actual source advisory through a purpose-built review UI backed by Postgres.



2\. Rigorous, reproducible evaluation



Baseline and fine-tuned models are scored with the identical harness, on the identical test sets, at temperature=0. In-distribution and out-of-distribution performance are reported and compared separately — not averaged together into one misleading number.



3\. A working hallucination safeguard



The model — like most small LLMs — will confidently invent specific details when they aren't in the source text. A prompt instruction alone was tested and found ineffective. A code-level groundedness check verifies every specific claim (CVE ID, product name, version range) against the literal source text and nulls out anything unverified, with the removal surfaced transparently in the UI rather than hidden.



4\. Live extraction interface



Paste any security advisory and get back structured, schema-valid, groundedness-checked JSON in real time — not just a static demo of pre-loaded examples.



Running locally



Prerequisites: Docker Desktop, Python 3.12, an NVIDIA GPU with ≥8GB VRAM for training/inference (CPU inference is possible but slow).



bash

\# 1. Start Postgres

docker compose up -d postgres



\# 2. Set up the environment

python -m venv venv

venv\\Scripts\\activate          # Windows

pip install -r requirements.txt



\# 3. Configure environment variables

copy .env.example .env         # fill in GITHUB\_TOKEN if rebuilding the dataset from scratch



\# 4. Start the backend (preloads the fine-tuned model — takes a moment)

uvicorn app.main:app --reload



\# 5. In a separate terminal, serve the frontend

cd frontend

python -m http.server 5500



Then open http://localhost:5500/extract.html to run live extractions, or http://localhost:5500/review.html for the label-review tool.



Note: the merged fine-tuned model checkpoint (checkpoints/secex\_merged\_v1) is not committed to this repo (large binary). To reproduce it, run the training pipeline end-to-end — see app/train/ for the QLoRA training script and app/train/merge\_adapter.py for the merge step. Full step-by-step methodology is in FINDINGS.md.



Project structure

secex-sft/

├── app/

│   ├── data\_pipeline/     # GHSA fetch, schema mapping, DB loading

│   ├── eval/              # scoring harness, baseline + fine-tuned eval runners

│   ├── routers/           # FastAPI routes (review, extract)

│   ├── schema/             # Pydantic extraction schema

│   ├── serving/           # inference logic + groundedness check

│   └── train/             # QLoRA training, merging, environment checks

├── data/

│   ├── clean/             # verified dataset, mapped labels

│   └── splits/            # train/val/id\_test/ood\_test

├── frontend/

│   ├── extract.html       # live extraction UI

│   └── review.html        # label review tool

├── tests/

├── FINDINGS.md            # full methodology, every finding, honest limitations

└── docker-compose.yml

Known limitations



This is documented in full in FINDINGS.md, but the short version:



Fine-tuning does not generalize to genuinely novel CWE categories, and may actively hurt performance there relative to the base model

The groundedness check covers structured fields (CVE ID, product, version) and detects — but does not auto-correct — leakage into free-text fields; a fabricated detail can still appear in prose even after being correctly stripped from structured output

146 training examples is small; some results (especially the 16-item OOD test set) carry real sample-size uncertainty

The one confirmed case of a hallucinated label surviving human review during dataset construction was documented rather than silently fixed

Roadmap

&#x20;Deploy merged model to Hugging Face Spaces; backend + frontend to Render

&#x20;Investigate the CVE ID accuracy regression after fine-tuning

&#x20;Extend automated test coverage to the groundedness check and /extract endpoint

&#x20;CI via GitHub Actions

