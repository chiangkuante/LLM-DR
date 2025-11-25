# LLM Digital Resilience Quantification System
# 企業數位韌性量化系統

使用本地端 LLM 分析 SEC 10-K 年報，量化 S&P 500 企業（2015-2024）的「數位韌性」分數。

## 快速開始

### 1. 建置環境

```bash
# 安裝依賴（推薦）
uv sync

# 若需額外套件，以 uv add 管理
uv add streamlit pandas beautifulsoup4 lxml tqdm plotly langchain "llama-cpp-python"

# 以 pip 方式（不建議）
pip install -e .
```

> **CUDA 注意**：`llama-cpp-python` 需具備對應 GPU 驅動與 CUDA Toolkit，若要啟用 GPU 推論請使用我方提供的 CMake 預編譯輪檔或自行編譯 `-DLLAMA_CUBLAS=on`。

### 2. 啟動 Streamlit GUI

```bash
streamlit run app.py
```

### 3. 命令列流程

```bash
# 10-K 前處理（委派至 src.preprocess）
python preprocess.py

# 量化評分（預設會跑六個 Agent，耗時較久）
PYTHONPATH=src python src/quantify.py

# 或匯入模組自行呼叫
PYTHONPATH=src python - <<'PY'
from src.quantify import score_resilience, LLMWrapper, load_cleaned_report
data = load_cleaned_report("AAPL", 2024)
wrapper = LLMWrapper()
print(score_resilience(wrapper, "AAPL", 2024, data))
PY
```

### 4. 使用 Jupyter Notebooks

```bash
jupyter notebook notebooks/
```

## 專案結構

```
├── src/                    # 核心模組
│   ├── apps/
│   │   └── streamlit_app.py   # Streamlit 多頁面邏輯
│   ├── tools/                 # CLI/輔助腳本
│   │   ├── filter_companies.py
│   │   ├── hg_downloader.py
│   │   └── sec_edgar_cli.py
│   ├── downloader.py          # 下載 10-K 報告
│   ├── preprocess.py          # 前處理與章節提取
│   ├── quantify.py            # 新版 AI 量化評分
│   ├── quantify_v1.py         # 舊版兩階段評分 (相容用途)
│   ├── quantify_v2_backup.py  # 備份版本
│   └── utils.py               # 工具函式
├── data/                  # 資料目錄
│   ├── 10k_raw/          # 原始報告
│   ├── 10k_cleaned/      # 清理後 JSON
│   ├── scores/           # 評分結果
│   └── trends/           # 趨勢分析
├── notebooks/            # Jupyter Notebooks
├── models/               # LLM 模型
├── tests/                # 快速驗證腳本
└── app.py               # Streamlit 主程式
```

## 功能

### 已完成
- 資料下載器 (444 家公司, 2015-2024)
- 前處理系統 (章節提取)
- Streamlit 基礎框架

### 開發中
- AI 量化評分系統 (多代理人架構)
- 結果視覺化
- 趨勢分析

## 技術堆疊

- **UI**: Streamlit
- **LLM**: llama-cpp-python (CUDA)
- **Model**: gpt-oss-20b-Q8_0.gguf (128K context)
- **Framework**: LangChain
- **Package Manager**: uv

## 參考文件

- `plan.md` - 專案規劃
- `AI_todo.md` - 開發任務清單
- `CLAUDE.md` - AI 助手指引

## 操作注意事項

- 需自行準備 `models/gpt-oss-20b-Q8_0.gguf` 或其他支援的 GGUF 檔案。
- 量化流程極耗 GPU 記憶體。預設 `n_ctx=128000`、`n_gpu_layers=-1`，若硬體不足可在 `src/quantify.py` 調整。
- 若僅需局部測試，可在 `score_resilience` 或 `test_scoring` 中限制要跑的維度，以縮短時間。
- 所有匯入建議透過 `PYTHONPATH=src` 或在程式內 `sys.path.insert(0, "src")`，以確保模組解析正確。

NPUST DN_LAB
