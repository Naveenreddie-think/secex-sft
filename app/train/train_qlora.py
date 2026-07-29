"""
QLoRA SFT training on the security advisory extraction dataset.
Run as: python -m app.train.train_qlora --limit 15   (small test run first)
Then:   python -m app.train.train_qlora              (full training run)
"""

import argparse

from unsloth import FastLanguageModel
from datasets import Dataset
from trl import SFTTrainer, SFTConfig


from app.train.format_dataset import load_formatted

MODEL_NAME = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048
OUTPUT_DIR = "checkpoints/secex_lora_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit train examples for a quick test run")
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    print("Loading base model (4-bit)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )

    print("Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    print("Formatting training/validation data...")
    train_texts = load_formatted("train", tokenizer, limit=args.limit)
    val_texts = load_formatted("val", tokenizer, limit=None)

    train_dataset = Dataset.from_dict({"text": train_texts})
    val_dataset = Dataset.from_dict({"text": val_texts})

    print(f"Train examples: {len(train_dataset)}  |  Val examples: {len(val_dataset)}")

    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
	per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=2e-4,
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        optim="adamw_8bit",
        seed=42,
        report_to="none",
        max_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
	eos_token=tokenizer.eos_token,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    print("Starting training...")
    result = trainer.train()

    print("\n--- Training complete ---")
    print(result)

    adapter_path = f"{OUTPUT_DIR}/final_adapter"
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"\nSaved adapter to {adapter_path}")


if __name__ == "__main__":
    main()