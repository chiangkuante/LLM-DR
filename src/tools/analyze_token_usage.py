import json
import logging
from pathlib import Path
from typing import Dict, List
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path("data/10k_cleaned")
SECTIONS_TO_CHECK = [
    "item_1", "item_1a", "item_1b", "item_1c", "item_2", "item_3", "item_4",
    "item_5", "item_6", "item_7", "item_7a", "item_8", "item_9", "item_9a", "item_9b",
    "item_10", "item_11", "item_12", "item_13", "item_14", "item_15",
    "cybersecurity", "esg_sustainability", "information_security"
]

def analyze_tokens():
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        return

    logger.info(f"Scanning files in {DATA_DIR}...")
    
    # Store stats: section -> {max_chars: int, max_tokens: int, file: str}
    stats = {sec: {"max_chars": 0, "max_tokens": 0, "file": ""} for sec in SECTIONS_TO_CHECK}
    
    files = list(DATA_DIR.glob("*.json"))
    logger.info(f"Found {len(files)} files.")

    for file_path in files:
        try:
            content = json.loads(file_path.read_text(encoding="utf-8"))
            company = content.get("company", "Unknown")
            year = content.get("year", "Unknown")
            file_label = f"{company} ({year})"

            for section in SECTIONS_TO_CHECK:
                text = content.get(section, "")
                if text:
                    char_len = len(text)
                    # Estimate tokens: 1 token ~= 4 chars (Conservative estimate for English)
                    token_est = int(char_len / 4)
                    
                    if char_len > stats[section]["max_chars"]:
                        stats[section]["max_chars"] = char_len
                        stats[section]["max_tokens"] = token_est
                        stats[section]["file"] = file_label
                        
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {e}")

    # Print Report
    print("\n" + "="*80)
    print(f"{'SECTION':<20} | {'MAX CHARS':<12} | {'EST TOKENS':<12} | {'SOURCE':<30}")
    print("-" * 80)
    
    for section in SECTIONS_TO_CHECK:
        data = stats[section]
        if data["max_chars"] > 0:
            print(f"{section:<20} | {data['max_chars']:<12,} | {data['max_tokens']:<12,} | {data['file']:<30}")
    print("="*80 + "\n")
    
    print("Note: Token count is estimated as (Characters / 4). Actual tokens may vary by tokenizer.")

if __name__ == "__main__":
    analyze_tokens()
