"""
DPO training on top of the existing SFT adapter (base+adapter, not merged).
Run as: python -m app.train_dpo.train_dpo --limit 15   (small test first)
Then:   python -m app.train_dpo.train_dpo              (full run)
"""
import sys
import types
import importlib.machinery

# trl's DPOTrainer eagerly imports an optional LLM-judge feature (llm_blender)
# that we don't use (we use the groundedness checker as our judge instead).
# llm_blender's installed version is incompatible with our pinned transformers
# version (references a removed constant). Stub it out before trl imports it,
# so trl's own import succeeds without needing the real, broken package.
_stub = types.ModuleType("llm_blender")
_stub.__spec__ = importlib.machinery.ModuleSpec("llm_blender", loader=None)
sys.modules["llm_blender"] = _stub

import argparse
from datasets import Dataset
from trl import DPOTrainer, DPOConfig
from unsloth import FastLanguageModel
from app.train_dpo.format_dpo_dataset import load_dpo_dataset

SFT_ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
MAX_SEQ_LENGTH = 2048
OUTPUT_DIR = "checkpoints/secex_dpo_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()

    print("Loading base model + existing SFT adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=SFT_ADAPTER_PATH,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )

    FastLanguageModel.for_training(model)
    model.warnings_issued = {}

    print("Formatting preference dataset...")
    data = load_dpo_dataset(tokenizer, path="data/preference/pairs_filtered.json", limit=args.limit)
    dataset = Dataset.from_list(data)
    print(f"DPO training examples: {len(dataset)}")

    training_args = DPOConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=5e-5,
        logging_steps=1,
        save_strategy="no",
        optim="adamw_8bit",
        seed=42,
        report_to="none",
        max_length=1024,
        max_prompt_length=800,
        max_completion_length=224,
        beta=0.1,
        precompute_ref_log_probs=True,
        precompute_ref_batch_size=1,
        use_liger_loss=True,
    )

    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    print("Starting DPO training...")
    result = trainer.train()

    print("\n--- DPO training complete ---")
    print(result)

    adapter_path = f"{OUTPUT_DIR}/final_adapter"
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"\nSaved DPO adapter to {adapter_path}")


if __name__ == "__main__":
    main()