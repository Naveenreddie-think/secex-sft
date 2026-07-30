"""
Pushes the merged fine-tuned model to a Hugging Face model repo.
Run as: python -m app.train.push_to_hub
"""

from huggingface_hub import HfApi, create_repo

from app.config import settings

MERGED_MODEL_PATH = "checkpoints/secex_merged_v1"
REPO_ID = "Nawin21/secex-sft-qwen2.5-3b"  # change if you want a different name/namespace


def main():
    api = HfApi(token=settings.hf_token)

    print(f"Creating repo (if it doesn't exist): {REPO_ID}")
    create_repo(REPO_ID, token=settings.hf_token, exist_ok=True, repo_type="model")

    print(f"Uploading {MERGED_MODEL_PATH} to {REPO_ID}...")
    api.upload_folder(
        folder_path=MERGED_MODEL_PATH,
        repo_id=REPO_ID,
        repo_type="model",
    )

    print(f"\nDone. Model available at: https://huggingface.co/{REPO_ID}")


if __name__ == "__main__":
    main()