"""
Formats pairs.json into the prompt/chosen/rejected structure trl's
DPOTrainer expects.
"""

import json
from pathlib import Path

from app.serving.prompts import SYSTEM_INSTRUCTION


def build_prompt_text(tokenizer, input_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": input_text[:4000]},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def load_dpo_dataset(tokenizer, path: str = "data/preference/pairs.json", limit: int | None = None) -> list[dict]:
    pairs = json.loads(Path(path).read_text(encoding="utf-8"))
    if limit:
        pairs = pairs[:limit]

    formatted = []
    for p in pairs:
        prompt = build_prompt_text(tokenizer, p["input_text"])
        formatted.append({
            "prompt": prompt,
            "chosen": p["chosen"],
            "rejected": p["rejected"],
        })
    return formatted