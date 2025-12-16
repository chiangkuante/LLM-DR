# AGENTS.md

This file provides guidance to CODEX when working with code in this repository.

## Output rules
Output language is Traditional Chinese
Please do not use any emojis; please use plain text.

## Project Overview

**Digital Resilience Quantification System (企業數位韌性量化系統)**

This system uses a local LLM to analyze SEC 10-K annual reports from S&P 500 companies (2015-2024) and quantify their "Digital Resilience" scores through a multi-agent evaluation framework.

**Core Technology Stack:**
- **Package Management**: `uv` (必須使用 `uv lock` 確保依賴一致性)
- **UI**: Streamlit (multi-page architecture)
- **LLM Framework**: LangChain
- **Inference Engine**: llama-server (OpenAI Compatible API) with CUDA acceleration
- **Model**: gpt-oss-20b-Q8_0.gguf (128K context window)
- **Language**: Python 3.x

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Generate lock file after adding dependencies
uv lock
```

### Running the Application
```bash
# Launch Streamlit GUI
streamlit run app.py

# Run preprocessing on raw 10-K files
python preprocess.py  # or use Streamlit UI

# Test with Jupyter notebooks
jupyter notebook notebooks/01_preprocess.ipynb
```

### Development Workflow
```bash
# Import modules from src/ in notebooks or scripts
import sys
sys.path.insert(0, 'src')
from preprocess import process_html_file
```

## Architecture & Key Design Decisions

### Data Pipeline (3-Phase Architecture)

**Current Status (2025-11-17):**
- Phase 0 & 1: Complete (downloader + preprocessing)
- Phase 2: Active (Quantification System v3)
- Phase 3: Planned (Streamlit enhancements)

**Phase 1: Preprocessing** (`preprocess.py` → `src/preprocess.py`)
- Input: Raw HTML from `data/10k_raw/`
- Output: Cleaned JSON in `data/10k_cleaned/`
- Extracts: Item 1, 1A, 1C, 7, 7A, 9A + Cybersecurity/InfoSec/ESG sections
- Uses BeautifulSoup + regex patterns to identify and extract sections
- **Critical**: Regex patterns avoid false positives (e.g., Item 10/12 vs Item 1)

**Phase 2: Quantification** (`src/quantify.py`)
- **Combined Architecture**: Smart Context Selection + 128K Window
- **Multi-Agent System (6+1 Agents)**:
  - **6 Domain Agents**: Absorb, Adopt, Transform, Anticipate, Rebound, Learn (Independent scoring)
  - **1 Reviewer Agent**: Validates all scores for consistency and evidence quality
- **Inference Strategy**:
  - Uses `llama-server` (server-client architecture) for stability
  - **Context Isolation**: Uses `reset_cache()` between agents to prevent attention drift
  - **Robustness**: Implements `json_repair` and adaptive retry logic for JSON parsing
- Input: `data/10k_cleaned/*.json` (one company-year at a time)
- Output: `data/scores/` with structured scoring + reasoning
- Processing: Single company (10 years) takes ~10 mins per run

**Phase 3: Streamlit Integration**
- Build UI framework FIRST (in Phase 0) before backend implementation
- Pages:
  1. Data Management (preprocessing controls)
  2. Quantification Control (company/year selection, start button)
  3. Results Visualization (charts, tables, export)
  4. Company Comparison (multi-company trends)
  5. Settings (model params, prompts, system monitoring)

### Directory Structure

```
project_root/
├── models/
│   └── gpt-oss-20b-Q8_0.gguf          # 12GB quantified model
├── data/
│   ├── 10k_raw/                        # 444 companies × 10 years
│   ├── 10k_cleaned/                    # Extracted sections (JSON)
│   ├── scores/                         # Quantification results (TODO)
│   └── trends/                         # Multi-year analysis (TODO)
├── notebooks/                          # Jupyter for testing
│   ├── 00_downloader.ipynb
│   ├── 01_preprocess.ipynb
│   └── 02_quantify.ipynb              # TODO
├── src/                                # Core modules
│   ├── __init__.py
│   ├── apps/
│   │   └── streamlit_app.py
│   ├── tools/
│   │   ├── filter_companies.py
│   │   ├── hg_downloader.py
│   │   └── sec_edgar_cli.py
│   ├── downloader.py
│   ├── preprocess.py
│   ├── quantify.py                    # Core Scoring Logic (6 Agents + Reviewer)
│   ├── quantify_v1.py                 # Legacy two-stage scoring
│   ├── quantify_v2_backup.py
│   └── utils.py                       # Logging, config
├── tests/
│   ├── test_quick_score.py
│   ├── test_quick_scoring_standalone.py
│   └── test_reasoning_suppression.py
└── app.py                             # Streamlit entry point (delegates to src apps)
```

**Current State**: 核心模組已移至 `src/`（apps、tools、pipeline 模組），請持續在該目錄內擴充。

### Critical Implementation Notes

#### LLM Configuration (llama-server)
- **Startup**: Managed via `src/tools/launch_server.sh`
- **Context**: 128K (gemma-2-27b / gpt-oss-20b)
- **Server Flags**: `-c 128000 -ngl 99 --parallel 1`
- **Client**: Standard OpenAI API client (`src/utils.py`)


#### Path Handling
- **Always use `pathlib.Path`** for cross-platform compatibility
- Fixed paths in `src/preprocess.py`:
  - `IN_ROOT = Path("data/10k_raw").resolve()`
  - `OUT_DIR = Path("data/10k_cleaned").resolve()`

#### Progress Tracking
- Use `tqdm` for CLI scripts
- Convert to Streamlit progress bars in `app.py`
- All long-running operations (downloads, inference) need progress indicators

#### Error Handling Strategy
- Checkpoint mechanism: Resume from failure (4440 inference calls)
- Batch processing: Process 10-50 companies at a time
- Token counting: Check if reports exceed 128K limit before processing
- Fallback: If too long, prioritize Item 1A, 7, 9A, Cybersecurity sections

### Multi-Agent Scoring System (Core Logic)

**Agent Prompt Structure (e.g., Absorb Agent):**
```
You are an expert analyst...
[Context limited to: Item 1A, Item 7, etc.]
Evaluate ABSORB capability...
Output JSON with: score, evidence, reasoning
```

**Reviewer Agent Structure:**
```
Review the following scores...
Verify evidence quality and logic consistency.
Output: APPROVED or CORRECTED with final score.
```

**Output Format:**
```json
{
  "company": "AAPL",
  "year": 2024,
  "overall_score": 78.5,
  "confidence": 0.85,
  "section_scores": {
    "item_1": 75.0,
    "item_1a": 82.0,
    "item_7": 77.5
  },
  "key_findings": ["強大的資安揭露", "成熟的事件應變"],
  "trend_analysis": {
    "2015_2024_change": +12.3,
    "trend": "improving"
  }
}
```

## Important Considerations

### Performance Expectations
- Single company (10 years): <10 minutes
- Full dataset (4440 reports): <72 hours
- Per-report inference: 30-60 seconds (128K context)

### Data Scope
- **Completed**: 444 companies with 10-K reports (2015-2024)
- **Target**: S&P 500 companies
- Some companies may have <10 reports (filtered out)

### Dependencies to Add (pyproject.toml)
```toml
langchain
openai
streamlit
pandas
beautifulsoup4
lxml
tqdm
plotly
json_repair
```

### Code Style Guidelines (from plan.md)
- Use `pathlib` for all path operations
- Include logging/print for long-running operations
- Consider LLM context window limits in implementations
- Notebooks should import from `src/` modules for consistency

## Current Development Priority (Phase 3)

1. **Data Analysis**: Analyze Phase 2 quantification results (`notebooks/`)
2. **Streamlit Visualization**: Build advanced charts for multi-year trends
3. **Optimizing**: Fine-tune Agent prompts and context selection
4. **Reporting**: Generate aggregate reports for S&P 500

Refer to `AI_todo.md` for detailed task breakdown and `plan.md` for original specifications.
