"""
Sanity check: loads the merged model and runs a real extraction to confirm
it matches the quality we saw from the adapter-based eval.
Run as: python -m app.train.test_merged
"""

import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.serving.prompts import SYSTEM_INSTRUCTION
from app.serving.groundedness import check_groundedness

MERGED_PATH = "checkpoints/secex_merged_v1"

SAMPLE_ADVISORY = """### Impact
A network attacker who can reach the admin API can bypass authentication entirely by sending a request with an empty Authorization header, due to a logic error that treats an empty string as a valid bypass token.

### Patches
Patched in v2.3.1. Upgrade immediately."""


def main():
    print("Loading merged model (this may take a minute)...")
    tokenizer = AutoTokenizer.from_pretrained(MERGED_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MERGED_PATH,
        dtype=torch.bfloat16,
        device_map="cuda",
    )

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": SAMPLE_ADVISORY},
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

    print("\n--- Raw model output ---")
    print(raw_output)

    try:
        parsed = json.loads(raw_output.strip().replace("```json", "").replace("```", ""))
        print("\n--- Parsed successfully (before groundedness check) ---")
        print(json.dumps(parsed, indent=2))

        checked, warnings = check_groundedness(parsed, SAMPLE_ADVISORY)
        print("\n--- After groundedness check ---")
        print(json.dumps(checked, indent=2))
        print(f"\nWarnings: {warnings}")
    except json.JSONDecodeError as e:
        print(f"\n--- JSON parse failed: {e} ---")


if __name__ == "__main__":
    main()