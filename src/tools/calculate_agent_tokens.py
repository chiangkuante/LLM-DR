#!/usr/bin/env python3
import json
import statistics
from pathlib import Path
from typing import Dict, List

# Define the Agent-Section Mapping (from src/quantify.py)
AGENT_SECTION_MAPPING = {
    "absorb": [
        "item_1a",            # Risk Factors
        "item_9a",            # Controls & Procedures
        "item_1c",            # Cybersecurity
        "cybersecurity",      # Extra
        "information_security", # Extra
    ],
    "adopt": [
        "item_7",             # MD&A
        "item_1",             # Business
        "item_1a",            # Risk Factors (partial context)
    ],
    "transform": [
        "item_7",             # MD&A
        "item_1",             # Business
        "esg_sustainability", # ESG
    ],
    "anticipate": [
        "item_1a",            # Risk Factors
        "item_1c",            # Cybersecurity
        "cybersecurity",      # Extra
        "item_9a",            # Controls
    ],
    "rebound": [
        "item_1c",            # Cybersecurity
        "cybersecurity",      # Extra
        "item_9a",            # Controls
        "item_7",             # MD&A (partial)
    ],
    "learn": [
        "esg_sustainability", # ESG
        "item_9a",            # Internal audit
        "item_1a",            # Risk Factors
    ],
}

DATA_DIR = Path("data/10k_cleaned")

def calculate_tokens():
    # Find all AAPL files
    aapl_files = sorted(list(DATA_DIR.glob("AAPL_10-K_*.json")))
    
    if not aapl_files:
        print("No AAPL files found in data/10k_cleaned")
        return

    print(f"Found {len(aapl_files)} AAPL reports. Calculating token usage...\n")

    agent_usage = {agent: [] for agent in AGENT_SECTION_MAPPING}

    for file_path in aapl_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Identify year from filename or content (optional, just logging)
            filename = file_path.name
            
            for agent, sections in AGENT_SECTION_MAPPING.items():
                total_chars = 0
                for section in sections:
                    content = data.get(section, "")
                    if content:
                        # Append header overhead per section logic in quantify.py
                        # header = f"\n\n=== {section_key.upper()} ===\n\n"
                        header_len = len(f"\n\n=== {section.upper()} ===\n\n")
                        total_chars += len(content) + header_len
                
                # Estimate tokens: chars / 4
                tokens = total_chars / 4
                agent_usage[agent].append(tokens)
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Calculate statistics
    print(f"{'Agent':<15} | {'Avg Tokens':<15} | {'Min':<10} | {'Max':<10}")
    print("-" * 60)
    
    total_avg = 0
    for agent, tokens_list in agent_usage.items():
        if not tokens_list:
            print(f"{agent:<15} | N/A")
            continue
            
        avg = statistics.mean(tokens_list)
        min_t = min(tokens_list)
        max_t = max(tokens_list)
        
        print(f"{agent:<15} | {avg:,.0f}            | {min_t:,.0f}      | {max_t:,.0f}")
        total_avg += avg

    print("-" * 60)
    print(f"{'TOTAL per Report':<15} | {total_avg:,.0f} (Sum of avgs)")

if __name__ == "__main__":
    calculate_tokens()
