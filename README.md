# LLM Digital Resilience Quantification System
# 企業數位韌性量化系統

使用本地端 LLM 分析 SEC 10-K 年報，量化 S&P 500 企業（2015-2024）的「數位韌性」分數。

## 快速開始

### 1. 安裝依賴

```bash
# 使用 uv 安裝
uv sync

# 或使用 pip
pip install -e .
```

### 2. 啟動 Streamlit GUI

```bash
streamlit run app.py
```

### 3. 使用 Jupyter Notebooks

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

### ✅ 已完成
- 資料下載器 (444 家公司, 2015-2024)
- 前處理系統 (章節提取)
- Streamlit 基礎框架

### 🚧 開發中
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

## License

MIT License

## Contributors

NPUST MIS Lab © 2024
