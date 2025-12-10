import argparse
import logging
from pathlib import Path
from huggingface_hub import snapshot_download

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default Configuration per GEMINI.md 
# DEFAULT_REPO_ID = "unsloth/gpt-oss-20b-GGUF" # Assumed based on file name match, verify if needed
# DEFAULT_FILENAME = "gpt-oss-20b-Q8_0.gguf"
DEFAULT_REPO_ID = "unsloth/Ministral-3-14B-Instruct-2512-GGUF" # Assumed based on file name match, verify if needed
DEFAULT_FILENAME = "Ministral-3-14B-Instruct-2512-Q6_K.gguf"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"

def download_model(repo_id: str, filename: str, model_dir: Path, force: bool = False):
    """
    Downloads a specific model file from Hugging Face Hub.
    """
    model_dir.mkdir(parents=True, exist_ok=True)
    target_file = model_dir / filename
    
    if target_file.exists() and not force:
        logger.info(f"Model file already exists at {target_file}. Use --force to overwrite.")
        return

    logger.info(f"Downloading {filename} from {repo_id} to {model_dir}...")
    
    try:
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=model_dir,
            allow_patterns=[filename],
            local_dir_use_symlinks=False,
            resume_download=True
        )
        logger.info(f"Successfully downloaded to: {downloaded_path}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Hugging Face models for LLM-DR")
    parser.add_argument("--repo_id", type=str, default=DEFAULT_REPO_ID, help="Hugging Face Repository ID")
    parser.add_argument("--filename", type=str, default=DEFAULT_FILENAME, help="Specific filename GGUF to download")
    parser.add_argument("--dir", type=Path, default=DEFAULT_MODEL_DIR, help="Directory to save the model")
    parser.add_argument("--force", action="store_true", help="Force download even if file exists")

    args = parser.parse_args()

    download_model(args.repo_id, args.filename, args.dir, args.force)