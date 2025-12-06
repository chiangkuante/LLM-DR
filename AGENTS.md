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
- **Inference Engine**: llama-cpp-python with CUDA GPU acceleration
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
- Phase 2: In development (quantification system)
- Phase 3: Planned (Streamlit enhancements)

**Phase 1: Preprocessing** (`preprocess.py` → `src/preprocess.py`)
- Input: Raw HTML from `data/10k_raw/`
- Output: Cleaned JSON in `data/10k_cleaned/`
- Extracts: Item 1, 1A, 1C, 7, 7A, 9A + Cybersecurity/InfoSec/ESG sections
- Uses BeautifulSoup + regex patterns to identify and extract sections
- **Critical**: Regex patterns avoid false positives (e.g., Item 10/12 vs Item 1)

**Phase 2: Quantification** (`src/quantify.py` - TO BE BUILT)
- **Key Architecture Change**: NO TEXT CHUNKING
- Processes entire annual reports in one pass (利用 128K context window)
- Multi-Agent System:
  - **Agent 1 (Scorer)**: Evaluates full report, outputs section scores + overall score
  - **Agent 2 (Reviewer)**: Validates Agent 1's assessment for consistency
- Input: `data/10k_cleaned/*.json` (one company-year at a time)
- Output: `data/scores/` with structured scoring + reasoning
- Processing: 444 companies × 10 years = 4440 inference calls (~37-74 hours total)

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
│   ├── quantify.py                    # TODO: Phase 2 ongoing
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

#### LLM Configuration (llama-cpp-python)
```python
# MUST set for CUDA acceleration
n_gpu_layers=-1  # Use all GPU layers

# Context window
n_ctx=128000     # 128K tokens to fit entire annual reports

# Scoring consistency
temperature=0.1-0.3  # Low for consistent scoring
```

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

**Agent 1 Prompt Structure:**
```
你是評估企業數位韌性的專家分析師...
[Few-shot 範例]
評估此公司的 10-K 年報（包含所有章節）並提供:
1. 各章節分數 (Item 1, 1A, 7, 7A, 9A, Cybersecurity, ESG)
2. 整體數位韌性分數 (0-100)
3. 關鍵證據
4. 評分推理
5. 信心水準
```

**Agent 2 Prompt Structure:**
```
審查以下數位韌性評估...
驗證:
1. 分數是否有證據支持？
2. 是否有遺漏的指標？
3. 是否有分數膨脹/緊縮？
4. 章節分數與整體分數是否一致？
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
llama-cpp-python[cuda]
streamlit
pandas
beautifulsoup4
lxml
tqdm
plotly
```

### Code Style Guidelines (from plan.md)
- Use `pathlib` for all path operations
- Include logging/print for long-running operations
- Consider LLM context window limits in implementations
- Notebooks should import from `src/` modules for consistency

## Current Development Priority (Week 1)

1. **Project restructuring**: Move files to `src/` directory
2. **Dependency setup**: Create `pyproject.toml` with `uv`
3. **Streamlit framework**: Build `app.py` with multi-page structure FIRST
4. **Integration**: Connect preprocessing to Streamlit UI

Refer to `AI_todo.md` for detailed task breakdown and `plan.md` for original specifications.
