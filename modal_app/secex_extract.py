"""
Modal app: serves the merged SecEx model as a web endpoint.
Deploy with: modal deploy modal_app/secex_extract.py
"""

import modal

app = modal.App("secex-extraction")

MODEL_ID = "Nawin21/secex-sft-qwen2.5-3b"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers>=4.51.3,<=5.5.0",
        "accelerate",
        "fastapi",
    )
)

SYSTEM_INSTRUCTION = """Extract structured vulnerability information from the security advisory text into JSON matching this exact schema:
{"vulnerabilities": [{"cve_id": string or null, "affected_products": [{"vendor": string, "product": string, "version_range": string or null}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}]}

CRITICAL: Only include a cve_id, vendor, product name, or version_range if that exact information is explicitly stated in the text. Never invent, guess, or infer specific identifiers, product names, or CVE numbers that are not literally present in the source text. If this information is not stated, use null (for cve_id, version_range) or omit the entry (for affected_products) rather than fabricating a plausible-sounding value.

Return ONLY valid JSON, no markdown fences, no preamble."""


@app.cls(image=image, gpu="T4", scaledown_window=120)
class SecExModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Loading model...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, dtype=torch.bfloat16, device_map="cuda"
        )
        print("Model loaded.")

    @modal.method()
    def extract(self, input_text: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": input_text[:4000]},
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        ).to("cuda")

        outputs = self.model.generate(
            **inputs, max_new_tokens=500, temperature=0.0, do_sample=False
        )
        raw_output = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        return raw_output


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def generate(item: dict):
    model = SecExModel()
    result = model.extract.remote(item["input_text"])
    return {"raw_output": result}