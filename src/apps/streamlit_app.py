"""
Streamlit 主程式 - 企業數位韌性量化系統
Digital Resilience Quantification System

多頁面架構:
- 頁面 1: 資料管理 (Data Management)
- 頁面 2: 量化評分 (Quantification)
- 頁面 3: 結果視覺化 (Results)
- 頁面 4: 公司比較 (Comparison)
- 頁面 5: 系統設定 (Settings)
"""

import streamlit as st
from ..utils import Config

def main():
    # 頁面設定
    st.set_page_config(
        page_title="數位韌性量化系統",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 確保目錄存在
    Config.ensure_directories()

    # 側邊欄 - 頁面導航
    st.sidebar.title("📊 數位韌性量化系統")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "選擇功能頁面",
        [
            "🏠 首頁",
            "📁 資料管理",
            "⚙️ 量化評分",
            "📈 結果視覺化",
            "🔍 公司比較",
            "⚙️ 系統設定"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        "**系統狀態**\n\n"
        f"- 原始資料: {len(list(Config.RAW_DATA_DIR.glob('*')))} 家公司\n"
        f"- 已清理: {len(list(Config.CLEANED_DATA_DIR.glob('*.json')))} 份報告\n"
        f"- 已評分: {len(list(Config.SCORES_DIR.glob('*.json')))} 份報告"
    )

    # 主要內容區域
    if page == "🏠 首頁":
        st.title("🏠 企業數位韌性量化系統")
        st.markdown("### Digital Resilience Quantification System")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="📊 資料範圍",
                value="2015-2024",
                delta="10 年份"
            )

        with col2:
            st.metric(
                label="🏢 目標公司",
                value="S&P 500",
                delta="444 家已下載"
            )

        with col3:
            st.metric(
                label="🤖 評分模型",
                value="GPT-OSS-20B",
                delta="128K context"
            )

        st.markdown("---")

        st.markdown("""
        ## 系統功能

        ### 📁 資料管理
        - 查看已下載的 10-K 報告
        - 執行批次前處理
        - 監控處理進度

        ### ⚙️ 量化評分
        - 選擇公司與年份
        - 啟動 AI 評分流程
        - 多代理人驗證機制

        ### 📈 結果視覺化
        - 單一公司趨勢分析
        - 章節分數詳細檢視
        - 匯出評分報告

        ### 🔍 公司比較
        - 多公司趨勢對比
        - 產業排名分析
        - 統計摘要報告

        ### ⚙️ 系統設定
        - 調整模型參數
        - 自定義評分標準
        - 系統資源監控
        """)

        st.markdown("---")
        st.info("👈 請從左側選單選擇功能頁面開始使用")

    elif page == "📁 資料管理":
        st.title("📁 資料管理")

        tab1, tab2 = st.tabs(["資料總覽", "前處理"])

        with tab1:
            st.subheader("已下載的 10-K 報告")

            # 掃描原始資料目錄
            raw_companies = list(Config.RAW_DATA_DIR.glob("*"))

            if raw_companies:
                st.success(f"找到 {len(raw_companies)} 家公司的資料")

                # 顯示前 10 家公司
                st.markdown("**公司列表 (前 10 家):**")
                for i, company_dir in enumerate(raw_companies[:10], 1):
                    company_name = company_dir.name
                    report_count = len(list((company_dir / "10-K").glob("*"))) if (company_dir / "10-K").exists() else 0
                    st.text(f"{i}. {company_name}: {report_count} 份報告")

                if len(raw_companies) > 10:
                    st.info(f"... 還有 {len(raw_companies) - 10} 家公司")
            else:
                st.warning("尚未下載任何 10-K 報告")

            st.markdown("---")

            # 已清理資料統計
            cleaned_files = list(Config.CLEANED_DATA_DIR.glob("*.json"))
            st.subheader("已清理的報告")
            st.metric("JSON 檔案數量", len(cleaned_files))

        with tab2:
            st.subheader("批次前處理")

            st.info("""
            前處理功能會:
            1. 讀取原始 HTML 格式的 10-K 報告
            2. 提取關鍵章節 (Item 1, 1A, 1C, 7, 7A, 9A, Cybersecurity, ESG)
            3. 清理雜訊並儲存為 JSON 格式
            """)

            # 檢查是否有原始資料
            raw_files = list(Config.RAW_DATA_DIR.rglob("*.html"))
            cleaned_files = list(Config.CLEANED_DATA_DIR.glob("*.json"))

            col1, col2 = st.columns(2)
            with col1:
                st.metric("待處理檔案", len(raw_files))
            with col2:
                st.metric("已處理檔案", len(cleaned_files))

            if len(raw_files) == 0:
                st.warning("⚠️ 未找到任何 HTML 檔案，請先下載 10-K 報告")
            else:
                if st.button("🚀 開始批次前處理", type="primary"):
                    from .. import preprocess as preprocess_module

                    process_batch = preprocess_module.process_batch

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        status_text.text("初始化處理...")

                        # 執行批次處理（不顯示 tqdm，因為在 Streamlit 中）
                        with st.spinner("正在處理 10-K 報告..."):
                            stats = process_batch(show_progress=False)

                        # 顯示結果
                        if stats["success"]:
                            progress_bar.progress(100)
                            st.success(f"✅ 處理完成！")

                            st.markdown("### 處理結果")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("總計", stats["total"])
                            with col2:
                                st.metric("成功", stats["processed"], delta=stats["processed"])
                            with col3:
                                st.metric("失敗", stats["failed"], delta=-stats["failed"] if stats["failed"] > 0 else 0)

                            # 顯示詳細結果（最多前 10 筆）
                            if stats["files"]:
                                st.markdown("### 處理詳情（前 10 筆）")
                                for item in stats["files"][:10]:
                                    if item["status"] == "success":
                                        st.text(f"✅ {item['source']} → {item['output']}")
                                    else:
                                        st.text(f"❌ {item['source']}: {item.get('error', 'Unknown error')}")
                        else:
                            st.error(f"❌ 處理失敗: {stats.get('error', 'Unknown error')}")

                    except Exception as e:
                        st.error(f"❌ 發生錯誤: {str(e)}")
                        st.exception(e)

    elif page == "⚙️ 量化評分":
        st.title("⚙️ 量化評分")

        st.info("""
        **評分流程**：選擇公司與年份 → Agent 1 分析報告 → 生成 5 維度評分 → 儲存結果

        ⚠️ 注意：每份報告約需 10-15 分鐘處理時間（使用 RTX 4090 GPU 加速）
        """)

        # 獲取可用公司列表
        @st.cache_data
        def get_available_companies():
            """獲取所有已清理報告的公司列表"""
            companies = set()
            for file in Config.CLEANED_DATA_DIR.glob("*_10-K_*.json"):
                # 提取公司代號 (例如: AAPL_10-K_xxx.json -> AAPL)
                ticker = file.name.split("_10-K_")[0]
                companies.add(ticker)
            return sorted(list(companies))

        @st.cache_data
        def get_available_years(company: str):
            """獲取特定公司的可用年份"""
            years = []
            for file in Config.CLEANED_DATA_DIR.glob(f"{company}_10-K_*.json"):
                # 從檔名提取年份 (例如: AAPL_10-K_xxx-24-xxx.json -> 2024)
                import re
                match = re.search(r'-(\d{2})-', file.name)
                if match:
                    year_short = match.group(1)
                    year = 2000 + int(year_short)
                    years.append(year)
            return sorted(years)

        companies = get_available_companies()

        if not companies:
            st.error("❌ 未找到已清理的報告，請先執行「資料管理」→「批次前處理」")
        else:
            st.success(f"✅ 找到 {len(companies)} 家公司的報告")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 📊 選擇評分目標")

                # 批次模式切換
                batch_mode = st.checkbox("批次評分模式", help="啟用後可選擇多家公司與多個年份")

                if batch_mode:
                    # 批次模式：多選
                    st.markdown("**公司選擇**")
                    select_all_companies = st.checkbox("全選所有公司", key="select_all_companies")

                    if select_all_companies:
                        selected_companies = companies
                        st.info(f"已選擇 {len(selected_companies)} 家公司")
                    else:
                        selected_companies = st.multiselect(
                            "選擇公司（可多選）",
                            companies,
                            default=[companies[0]] if companies else [],
                            help="按住 Ctrl/Cmd 多選"
                        )

                    # 年份選擇（基於第一家選定的公司）
                    if selected_companies:
                        first_company = selected_companies[0]
                        available_years = get_available_years(first_company)

                        st.markdown("**年份選擇**")
                        select_all_years = st.checkbox("全選所有年份", key="select_all_years")

                        if select_all_years:
                            selected_years = available_years
                            st.info(f"已選擇 {len(selected_years)} 個年份")
                        else:
                            selected_years = st.multiselect(
                                "選擇年份（可多選）",
                                available_years,
                                default=[available_years[-1]] if available_years else [],
                                help="按住 Ctrl/Cmd 多選"
                            )

                        # 計算總任務數
                        total_tasks = len(selected_companies) * len(selected_years)
                        st.warning(
                            f"⚠️ 將評分 **{len(selected_companies)} 家公司** × **{len(selected_years)} 個年份** "
                            f"= **{total_tasks} 份報告**\n\n"
                            f"預計總時間: {total_tasks * 12:.0f}-{total_tasks * 15:.0f} 分鐘"
                        )
                    else:
                        selected_years = []
                        st.warning("⚠️ 請至少選擇一家公司")

                else:
                    # 單一模式：單選
                    selected_company = st.selectbox(
                        "公司代號",
                        companies,
                        index=companies.index("AAPL") if "AAPL" in companies else 0,
                        help="選擇要評分的公司 ticker"
                    )

                    available_years = get_available_years(selected_company)

                    if available_years:
                        selected_year = st.selectbox(
                            "報告年份",
                            available_years,
                            index=len(available_years) - 1,  # 預設選最新年份
                            help="選擇要評分的年份"
                        )

                        st.info(f"📄 將評分: **{selected_company}** 的 **{selected_year}** 年度 10-K 報告")

                        # 轉換為列表格式以統一後續處理
                        selected_companies = [selected_company]
                        selected_years = [selected_year]
                    else:
                        st.warning(f"⚠️ {selected_company} 沒有可用的報告")
                        selected_companies = []
                        selected_years = []

            with col2:
                st.markdown("### ⚙️ 模型參數")

                temperature = st.number_input(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.2,
                    step=0.1,
                    help="較低溫度 (0.1-0.3) 提供更一致的評分"
                )

                max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=1000,
                    max_value=4096,
                    value=3000,
                    step=500,
                    help="生成評分的最大 token 數"
                )

            # 檢查是否已有評分
            if selected_companies and selected_years:
                # 檢查有多少已完成的評分
                completed_count = 0
                for company in selected_companies:
                    for year in selected_years:
                        score_file = Config.SCORES_DIR / f"{company}_{year}_score.json"
                        if score_file.exists():
                            completed_count += 1

                if completed_count > 0:
                    st.info(f"ℹ️ 已有 {completed_count} / {len(selected_companies) * len(selected_years)} 份報告完成評分")

                    if not batch_mode and completed_count == 1:
                        # 單一模式且已有評分，顯示查看選項
                        if st.checkbox("顯示現有評分"):
                            try:
                                import json
                                score_file = Config.SCORES_DIR / f"{selected_companies[0]}_{selected_years[0]}_score.json"
                                score_data = json.loads(score_file.read_text(encoding="utf-8"))
                                st.json(score_data)
                            except Exception as e:
                                st.error(f"讀取評分失敗: {e}")

                # 跳過已完成的選項
                skip_completed = st.checkbox(
                    "跳過已評分的報告",
                    value=True,
                    help="啟用後將自動跳過已有評分結果的報告"
                )

                st.markdown("---")

                if st.button("🚀 開始 AI 評分", type="primary", disabled=(not selected_companies or not selected_years)):
                    from ..quantify import (
                        LLMWrapper,
                        agent1_score_report,
                        load_cleaned_report,
                        save_score_to_file,
                    )

                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()
                    results_placeholder = st.empty()

                    # 建立任務列表
                    tasks = []
                    for company in selected_companies:
                        for year in selected_years:
                            score_file = Config.SCORES_DIR / f"{company}_{year}_score.json"
                            if skip_completed and score_file.exists():
                                continue  # 跳過已完成
                            tasks.append((company, year))

                    if not tasks:
                        st.warning("⚠️ 所有選定的報告都已完成評分")
                    else:
                        st.info(f"📋 待處理: {len(tasks)} 份報告")

                        try:
                            # 載入 LLM（所有任務共用一個 LLM 實例）
                            status_placeholder.info("🤖 載入 LLM 模型 (gpt-oss-20b)...")
                            wrapper = LLMWrapper()

                            if not wrapper.load_model():
                                st.error("❌ LLM 模型載入失敗，請檢查 models/ 目錄")
                            else:
                                st.success("✅ LLM 模型載入成功")

                                try:
                                    # 批次處理所有任務
                                    completed_tasks = []
                                    failed_tasks = []

                                    for idx, (company, year) in enumerate(tasks, 1):
                                        # 更新進度
                                        progress = idx / len(tasks)
                                        progress_placeholder.progress(progress)
                                        status_placeholder.info(
                                            f"⏳ 處理中: {company} ({year}) - {idx}/{len(tasks)}\n\n"
                                            f"預計剩餘時間: {(len(tasks) - idx) * 12:.0f}-{(len(tasks) - idx) * 15:.0f} 分鐘"
                                        )

                                        # 載入報告
                                        report_data = load_cleaned_report(company, year)

                                        if not report_data:
                                            failed_tasks.append((company, year, "無法載入報告"))
                                            continue

                                        # 執行評分
                                        with st.spinner(f"AI 評分中: {company} {year}..."):
                                            score = agent1_score_report(
                                                wrapper,
                                                company,
                                                year,
                                                report_data
                                            )

                                        if score:
                                            # 儲存結果
                                            output_path = save_score_to_file(score)
                                            completed_tasks.append((company, year, score.overall_score))
                                            st.success(f"✅ {company} ({year}): {score.overall_score:.1f}/100")
                                        else:
                                            failed_tasks.append((company, year, "評分失敗"))
                                            st.error(f"❌ {company} ({year}): 評分失敗")

                                    # 完成所有任務
                                    progress_placeholder.progress(1.0)
                                    status_placeholder.success(
                                        f"🎉 批次評分完成！\n\n"
                                        f"成功: {len(completed_tasks)} / 失敗: {len(failed_tasks)}"
                                    )

                                    # 顯示結果摘要
                                    st.markdown("---")
                                    st.markdown("## 📊 批次評分結果")

                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("成功", len(completed_tasks))
                                    with col2:
                                        st.metric("失敗", len(failed_tasks))

                                    # 成功列表
                                    if completed_tasks:
                                        st.markdown("### ✅ 成功完成")
                                        for company, year, score in completed_tasks:
                                            st.text(f"{company} ({year}): {score:.1f}/100")

                                    # 失敗列表
                                    if failed_tasks:
                                        st.markdown("### ❌ 失敗項目")
                                        for company, year, reason in failed_tasks:
                                            st.text(f"{company} ({year}): {reason}")

                                finally:
                                    wrapper.unload_model()
                                    st.info("🔓 LLM 模型已卸載")

                        except Exception as e:
                            st.error(f"❌ 發生錯誤: {str(e)}")
                            st.exception(e)

    elif page == "📈 結果視覺化":
        st.title("📈 結果視覺化")

        st.warning("🚧 此功能正在開發中")

        st.markdown("### 假資料示範")

        # 假資料圖表
        import pandas as pd
        import plotly.express as px

        # 生成假資料
        years = list(range(2015, 2025))
        scores = [65, 68, 70, 73, 75, 78, 80, 82, 85, 87]

        df = pd.DataFrame({
            "Year": years,
            "Score": scores
        })

        fig = px.line(df, x="Year", y="Score",
                      title="數位韌性分數趨勢 (假資料)",
                      markers=True)
        fig.update_layout(yaxis_range=[0, 100])

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 章節分數
        st.subheader("章節分數 (假資料)")
        section_data = pd.DataFrame({
            "章節": ["Item 1", "Item 1A", "Item 7", "Item 7A", "Item 9A"],
            "分數": [75, 82, 78, 70, 85]
        })

        fig2 = px.bar(section_data, x="章節", y="分數",
                      title="2024 年各章節分數")
        fig2.update_layout(yaxis_range=[0, 100])

        st.plotly_chart(fig2, use_container_width=True)

    elif page == "🔍 公司比較":
        st.title("🔍 公司比較")

        st.warning("🚧 此功能正在開發中")

        st.multiselect(
            "選擇要比較的公司",
            ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
            default=["AAPL", "MSFT", "GOOGL"]
        )

        st.markdown("### 多公司趨勢對比 (假資料)")

        import pandas as pd
        import plotly.express as px

        # 生成多公司假資料
        years = list(range(2015, 2025))

        data = []
        for company in ["AAPL", "MSFT", "GOOGL"]:
            for year in years:
                score = 60 + (year - 2015) * 2 + {"AAPL": 10, "MSFT": 5, "GOOGL": 0}[company]
                data.append({"Company": company, "Year": year, "Score": score})

        df = pd.DataFrame(data)

        fig = px.line(df, x="Year", y="Score", color="Company",
                      title="多公司數位韌性趨勢比較",
                      markers=True)
        fig.update_layout(yaxis_range=[0, 100])

        st.plotly_chart(fig, use_container_width=True)

    elif page == "⚙️ 系統設定":
        st.title("⚙️ 系統設定")

        tab1, tab2, tab3 = st.tabs(["模型參數", "評分標準", "系統監控"])

        with tab1:
            st.subheader("LLM 模型參數")

            col1, col2 = st.columns(2)

            with col1:
                st.number_input("Temperature", 0.0, 1.0, 0.2, 0.1, key="temp_setting")
                st.number_input("Top P", 0.0, 1.0, 0.9, 0.1, key="topp_setting")
                st.number_input("Context Length", 1024, 131072, 131072, 1024, key="ctx_setting")

            with col2:
                st.number_input("Max Tokens", 100, 4096, 2048, 100, key="max_tokens")
                st.number_input("GPU Layers", -1, 100, -1, 1, key="gpu_layers")
                st.checkbox("Use CUDA", value=True, key="use_cuda")

            if st.button("💾 儲存設定"):
                st.success("設定已儲存")

        with tab2:
            st.subheader("數位韌性評分標準")

            st.markdown("""
            ### 評分維度 (0-100 分)

            1. **資安態勢** (Cybersecurity Posture)
            2. **事件應對** (Incident Response)
            3. **數位轉型** (Digital Transformation)
            4. **業務持續性** (Business Continuity)
            5. **風險管理** (Risk Management)
            """)

            st.text_area("自定義評分標準", height=200, placeholder="輸入評分標準...")

        with tab3:
            st.subheader("系統監控")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("GPU 使用率", "N/A", "待實作")

            with col2:
                st.metric("記憶體使用", "N/A", "待實作")

            with col3:
                st.metric("磁碟空間", "N/A", "待實作")

            st.markdown("---")

            st.info("系統監控功能將在後續版本實作")

    # 頁尾
    st.sidebar.markdown("---")
    st.sidebar.markdown("**LLM Digital Resilience System v0.1.0**")
    st.sidebar.markdown("NPUST MIS Lab © 2024")

if __name__ == "__main__":
    main()
