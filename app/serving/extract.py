"""
Core extraction logic: runs the merged model and applies the groundedness check.
Shared by the FastAPI endpoint and any future CLI/batch tooling.
"""

import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.serving.prompts import SYSTEM_INSTRUCTION
from app.serving.groundedness import check_groundedness

MERGED_MODEL_PATH = "checkpoints/secex_merged_v1"

_model = None
_tokenizer = None


def load_model():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MERGED_MODEL_PATH)
        _model = AutoModelForCausalLM.from_pretrained(
            MERGED_MODEL_PATH,
            dtype=torch.bfloat16,
            device_map="cuda",
        )
    return _model, _tokenizer


def extract(input_text: str) -> dict:
    model, tokenizer = load_model()

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": input_text[:4000]},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to("cuda")

    outputs = model.generate(**inputs, max_new_tokens=500, temperature=0.0, do_sample=False)
    raw_output = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    cleaned = raw_output.strip().replace("```json", "").replace("```", "")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Model output was not valid JSON: {e}", "raw_output": raw_output}

    checked, warnings = check_groundedness(parsed, input_text)

    return {
        "success": True,
        "extraction": checked,
        "groundedness_warnings": warnings,
    }