# 引入 Downloader 類別
from sec_edgar_downloader import Downloader
from datetime import datetime

# --- 步驟 1: 初始化 Downloader ---
# 建立一個 Downloader 實例。
# SEC 要求使用者在請求的 User-Agent 中提供公司名稱和聯絡 Email，這是為了識別請求來源。
# 請務必替換成你自己的資訊，否則可能會被 SEC 封鎖請求。
# 第一個參數: 你的公司/組織名稱 (Your Company Name)
# 第二個參數: 你的 Email (Your Email Address)
dl = Downloader("NPUST MIS", "chiangkuante@gmail.com")

# --- 步驟 2: 設定要爬取的公司與文件類型 ---
# 設定美國sp500的股票代碼
tickers = ["NVDA","AAPL","MSFT","AMZN","GOOGL","AVGO","GOOG","META","TSLA","BRK-B","JPM","WMT","LLY","ORCL","V","MA","XOM","PLTR","NFLX","JNJ","AMD","COST","BAC","ABBV","HD","PG","GE","CVX","UNH","KO","CSCO","IBM","WFC","CAT","MS","MU","AXP","CRM","GS","RTX","TMUS","PM","APP","ABT","MRK","TMO","MCD","DIS","UBER","PEP","ANET","LRCX","LIN","QCOM","NOW","INTC","ISRG","INTU","AMAT","C","T","SCHW","APH","NEE","BLK","VZ","BKNG","AMGN","KLAC","GEV","TJX","ACN","BA","DHR","BSX","PANW","GILD","ETN","SPGI","TXN","ADBE","PFE","COF","CRWD","SYK","LOW","UNP","HOOD","HON","DE","WELL","PGR","CEG","MDT","PLD","ADI","BX","LMT","COP","VRTX","CB","DASH","DELL","KKR","ADP","HCA","SO","CMCSA","MCK","TT","CVS","PH","DUK","CME","NKE","MO","BMY","GD","COIN","CDNS","SBUX","MMM","NEM","MMC","MCO","SHW","SNPS","AMT","ICE","NOC","EQIX","HWM","UPS","WM","ORLY","EMR","RCL","ABNB","BK","JCI","MDLZ","TDG","CTAS","AON","TEL","USB","ECL","GLW","PNC","APO","ITW","MAR","WMB","ELV","REGN","MSI","CSX","PWR","FTNT","COR","CI","MNST","PYPL","RSG","GM","AEP","ADSK","AJG","WDAY","ZTS","VST","NSC","CL","AZO","CMI","SRE","TRV","FDX","FCX","HLT","MPC","DLR","KMI","EOG","AXON","SPG","AFL","TFC","DDOG","WBD","URI","PSX","STX","LHX","APD","SLB","MET","O","NXPI","F","VLO","ROST","PCAR","WDC","BDX","ALL","IDXX","CARR","D","EA","PSA","NDAQ","EW","MPWR","XEL","ROP","BKR","TTWO","FAST","GWW","EXC","AME","XYZ","CBRE","CAH","MSCI","DHI","AIG","ETR","AMP","KR","OKE","TGT","PAYX","CMG","CTVA","CPRT","A","FANG","ROK","GRMN","OXY","PEG","LVS","FICO","KMB","CCI","YUM","VMC","CCL","DAL","MLM","KDP","IQV","EBAY","XYL","PRU","WEC","OTIS","RMD","FI","SYY","CTSH","ED","PCG","WAB","EL","HIG","LYV","VTR","NUE","HSY","DD","GEHC","MCHP","HUM","EQT","NRG","TRGP","FIS","STT","HPE","VICI","ACGL","LEN","KEYS","RJF","IBKR","SMCI","VRSK","UAL","IRM","CHTR","EME","IR","WTW","ODFL","KHC","MTD","CSGP","ADM","K","TSCO","FSLR","TER","EXR","MTB","DTE","ROL","AEE","KVUE","ATO","FITB","ES","BRO","EXPE","WRB","PPL","SYF","FE","HPQ","EFX","BR","CBOE","AWK","HUBB","CNP","DOV","GIS","AVB","TDY","EXE","TTD","VLTO","LDOS","NTRS","HBAN","CINF","PTC","WSM","JBL","NTAP","PHM","ULTA","STE","STZ","STLD","TPR","DXCM","BIIB","EQR","HAL","TROW","CMS","VRSN","PODD","CFG","PPG","DG","TPL","RF","CHD","EIX","LH","DRI","CDW","WAT","L","DVN","TYL","SBAC","ON","IP","WST","LULU","DLTR","NI","ZBH","NVR","KEY","DGX","RL","SW","TRMB","BG","GPN","IT","J","PFG","CPAY","INCY","TSN","AMCR","CHRW","CTRA","GDDY","LII","GPC","EVRG","PKG","APTV","SNA","PNR","CNC","BBY","INVH","MKC","LNT","DOW","PSKY","WY","EXPD","HOLX","GEN","ESS","IFF","JBHT","FTV","LUV","TKO","ERIE","MAA","LYB","FFIV","OMC","ALLE","TXT","KIM","COO","UHS","FOX","CLX","ZBRA","FOXA","AVY","CF","DPZ","MAS","EG","NDSN","BF-B","BLDR","IEX","BALL","HII","REG","DOC","WYNN","DECK","SOLV","VTRS","HRL","BEN","ALB","SWKS","BXP","UDR","SJM","HST","DAY","RVTY","JKHY","AKAM","HAS","AIZ","GL","CPT","MRNA","PNW","IVZ","PAYC","SWK","NCLH","ARE","ALGN","FDS","POOL","NWSA","AES","GNRC","TECH","BAX","IPG","AOS","EPAM","CPB","CRL","MGM","MOS","TAP","LW","DVA","FRT","CAG","LKQ","APA","MOH","SOLSV","MTCH","HSIC","MHK","EMN","NWS"]


# 設定要爬取的文件類型。'10-K' 就是年報的代碼。
# 你也可以下載季報 '10-Q' 或重大事件報告 '8-K' 等。
filing_type = "10-K"

# --- 步驟 3: 設定日期範圍與下載數量 ---
# 設定日期範圍為2015-2024年
start_date = "2015-01-01"
end_date = "2024-12-31"

# --- 步驟 4: 執行下載 ---
# 使用 for 迴圈遍歷所有指定的公司
for ticker in tickers:
    try:
        print(f"正在處理 {ticker}...")
        # get 方法是核心下載函數
        # 參數說明:
        # 1. filing_type: 文件類型 ('10-K')
        # 2. ticker: 公司股票代碼 (例如 'AAPL')
        # 3. after: 開始日期 (可選)
        # 4. before: 結束日期 (可選)
        # 5. download_details: 是否下載包含詳細資訊的 HTML 文件，設為 True。
        num_filings_downloaded = dl.get(filing_type,
                                        ticker,
                                        after=start_date,
                                        before=end_date,
                                        download_details=True)

        if num_filings_downloaded < 10:
            print(f"⚠️  {ticker} 只下載到 {num_filings_downloaded} 份文件 (預期10份)")
            print(f"   可能原因: 該公司在指定期間內沒有提交完整的年報，或年報提交日期在範圍外")
        else:
            print(f"✅ 成功下載 {ticker} 的 {num_filings_downloaded} 份 2015-2024年 {filing_type} 年報。")

    except Exception as e:
        print(f"❌ 下載 {ticker} 的文件時發生錯誤: {e}")
        print(f"   建議: 檢查股票代碼是否正確，或該公司是否在SEC資料庫中")

print("\n" + "="*60)
print("美國企業2015-2024年10-K年報下載任務已完成。")
print(f"下載時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n說明:")
print("• 每家公司預期下載10份文件 (2015年至2024年的10-K年報)")
print("• 如果某家公司少於10份文件，可能是因為:")
print("  - 公司的會計年度結束日期導致年報提交時間落在範圍外")
print("  - 公司在該期間進行了重組或其他企業行為")
print("  - SEC資料庫中的資料完整性問題")
print("="*60)