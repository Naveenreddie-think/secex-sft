"""
Merges the trained LoRA adapter into the base model, producing a standalone
merged model ready for serving (locally or via HF Spaces later).
Run as: python -m app.train.merge_adapter
"""

from unsloth import FastLanguageModel

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
MERGED_OUTPUT_PATH = "checkpoints/secex_merged_v1"
MAX_SEQ_LENGTH = 2048


def main():
    print("Loading base model + adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )

    print("Merging adapter into base model (16-bit merge)...")
    model.save_pretrained_merged(
        MERGED_OUTPUT_PATH,
        tokenizer,
        save_method="merged_16bit",
    )

    print(f"Merged model saved to {MERGED_OUTPUT_PATH}")


if __name__ == "__main__":
    main()