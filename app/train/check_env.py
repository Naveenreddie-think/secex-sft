"""
Verifies GPU/CUDA setup and Unsloth model loading before writing training code.
Run as: python -m app.train.check_env
"""

import torch


def main():
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("CUDA NOT available — stop here, training will not work until this is fixed.")
        return

    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"CUDA capability: {torch.cuda.get_device_capability(0)}")
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    print("\nAttempting to load Qwen2.5-3B-Instruct via Unsloth (4-bit)...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    print("\nModel loaded successfully.")
    print(f"Model class: {type(model)}")

    # Quick smoke test — a single generation
    inputs = tokenizer("Hello, how are you?", return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=20)
    print(f"\nSmoke test output: {tokenizer.decode(outputs[0], skip_special_tokens=True)}")


if __name__ == "__main__":
    main()