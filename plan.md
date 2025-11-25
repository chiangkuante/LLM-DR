企業數位韌性量化系統 (Digital Resilience Quantification System)
1. 專案概述 (Project Overview)
本系統旨在利用本地端大型語言模型 (Local LLM)，針對 S&P 500 企業的 10-K 年報進行分析，量化其「數位韌性 (Digital Resilience)」分數。系統包含資料下載、前處理、文本分塊與多代理人 (Multi-Agent) 評分機制。

2. 技術堆疊 (Tech Stack)
環境與套件管理: uv (必須使用 uv lock 確保依賴一致性)

使用者介面 (GUI): Streamlit

LLM 框架: LangChain

推論引擎: llama-cpp-python (必須啟用 CUDA GPU 加速)

指定模型: gpt-oss-20b-Q8_0.gguf

核心語言: Python

3. 資料範圍 (Data Scope)
目標對象: S&P 500 成分股公司

時間跨度: 2015 - 2024 年

資料來源: SEC 10-K Filings

4. 專案結構 (Directory Structure)
請依照以下結構組織專案，確保 /src 中的邏輯與 .ipynb 筆記本可同步執行。

Plaintext

project_root/
├── .venv/                  # 由 uv 管理
├── pyproject.toml          # uv 依賴設定
├── uv.lock
├── models/
│   └── gpt-oss-20b-Q8_0.gguf
├── data/
│   ├── raw_10k/            # 原始年報
│   ├── processed_text/     # 清理後文本
│   └── chunks/             # 分塊後資料
├── notebooks/              # 用於實驗與展示的 Jupyter Notebooks
│   ├── 00_downloader.ipynb
│   ├── 01_preprocess.ipynb
│   ├── 02_chunker.ipynb
│   └── 03_quantify.ipynb
├── src/                    # 核心 Python 模組 (與 notebook 對應)
│   ├── __init__.py
│   ├── apps/
│   │   └── streamlit_app.py
│   ├── tools/
│   │   ├── filter_companies.py
│   │   ├── hg_downloader.py
│   │   └── sec_edgar_cli.py
│   ├── downloader.py       # Phase 0 下載
│   ├── preprocess.py       # Phase 1 前處理
│   ├── quantify.py         # Phase 2+ 新版量化
│   ├── quantify_v1.py      # Phase 2 舊版 (相容/測試)
│   ├── quantify_v2_backup.py
│   └── utils.py            # 共用工具 (logger, config)
├── tests/
│   ├── test_quick_score.py
│   ├── test_quick_scoring_standalone.py
│   └── test_reasoning_suppression.py
└── app.py                  # Streamlit 入口點
5. 執行階段詳解 (Execution Phases)
Phase 0: 下載器 (Downloader)
檔案: src/downloader.py / notebooks/00_downloader.ipynb

狀態: 已完成邏輯，待整合至專案結構。

功能:

檢查並下載指定模型 gpt-oss-20b-Q8_0.gguf 至 models/ 目錄。

批次下載 S&P 500 公司 2015-2024 的 10-K 文本。

Phase 1: 前處理 (Preprocess)
檔案: src/preprocess.py / notebooks/01_preprocess.ipynb

狀態: 已完成邏輯，待整合至專案結構。

功能:

清理原始 HTML/Text 格式。

去除雜訊 (Headers, Footers, 表格數據)，保留敘述性文本。

Phase 2: 文本分塊 (Chunker)
檔案: src/02_chunker.py / notebooks/02_chunker.ipynb

方法: 使用 LangChain 的 RecursiveCharacterTextSplitter。

需求:

設定適當的 chunk_size 與 chunk_overlap 以保留語意上下文。

將分塊後的資料序列化儲存 (如 JSON 或 VectorStore)，以供 Phase 3 使用。

Phase 3: 量化評分 (Quantify) - 核心邏輯
檔案: src/quantify.py / notebooks/03_quantify.ipynb

架構: Multi-Agent System (雙重角色驗證)。

流程:

Few-Shot Prompting: 載入預定義的「數位韌性」定義及少量評分範例。

Agent 1 (評分者): 針對每個 Chunk 或 Section 進行初步評分與理由闡述。

Agent 2 (審核者/整合者): 檢查 Agent 1 的產出，確保標準一致性，並修正偏差。

Aggregation (彙總):

Level 1: 彙總單一公司單一年度的分數。

Level 2: 產生該公司 2015-2024 的全年度趨勢報告。

硬體設定: 呼叫 llama-cpp 時務必設定 n_gpu_layers 以最大化利用 CUDA。

6. 使用者介面 (Streamlit GUI)
檔案: app.py

功能:

提供按鈕觸發上述各個 Phase。

視覺化進度條 (tqdm/streamlit progress)。

展示評分結果圖表 (折線圖顯示年度韌性變化)。

7. LLM 指令 (System Prompt for Coding)
若你需要產生程式碼，請遵循以下原則：

優先使用 pathlib 處理路徑。

所有耗時操作 (下載、推論) 需包含 logging 或 print 輸出以便追蹤。

LangChain 實作需考慮 Local Model 的 context window 限制。

確保 pyproject.toml 包含 langchain, llama-cpp-python, streamlit, pandas, beautifulsoup4 (依前處理需求) 等套件。