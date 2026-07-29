"""
Formats train/val splits into Qwen2.5 chat-template text ready for SFTTrainer.
Run as: python -m app.train.format_dataset
"""

import json
from pathlib import Path

SYSTEM_INSTRUCTION = """Extract structured vulnerability information from the security advisory text into JSON matching this exact schema:
{"vulnerabilities": [{"cve_id": string or null, "affected_products": [{"vendor": string, "product": string, "version_range": string or null}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}]}

Return ONLY valid JSON, no markdown fences, no preamble."""


def build_example(item: dict, tokenizer) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": item["input_text"][:4000]},
        {"role": "assistant", "content": json.dumps(item["label"])},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False)


def load_formatted(split_name: str, tokenizer, limit: int | None = None) -> list[str]:
    data = json.loads(Path(f"data/splits/{split_name}.json").read_text(encoding="utf-8"))
    if limit:
        data = data[:limit]
    return [build_example(item, tokenizer) for item in data]


if __name__ == "__main__":
    from unsloth import FastLanguageModel

    _, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    examples = load_formatted("train", tokenizer, limit=2)
    print("--- Example 1 formatted text ---")
    print(examples[0])
    print("\n--- Example 2 formatted text ---")
    print(examples[1])