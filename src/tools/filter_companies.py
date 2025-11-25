#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
篩選 sec-edgar-filings 目錄中的公司
刪除不足10份10-K年報的公司，並生成總結報告
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 設置 Windows 控制台編碼
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def count_10k_filings(company_path):
    """計算公司的10-K年報數量"""
    ten_k_path = company_path / "10-K"
    if not ten_k_path.exists():
        return 0

    try:
        # 計算10-K目錄下的子目錄數量（每個子目錄代表一份年報）
        filings = [d for d in ten_k_path.iterdir() if d.is_dir()]
        return len(filings)
    except Exception as e:
        print(f"錯誤：無法讀取 {company_path.name} 的年報：{e}")
        return 0

def main():
    base_dir = Path("sec-edgar-filings")

    if not base_dir.exists():
        print(f"錯誤：目錄 {base_dir} 不存在")
        return

    # 收集所有公司資訊
    companies_info = []
    removed_companies = []
    kept_companies = []

    print("正在掃描所有公司...")

    # 獲取所有公司目錄
    companies = sorted([d for d in base_dir.iterdir() if d.is_dir()])

    for company_dir in companies:
        company_name = company_dir.name
        filing_count = count_10k_filings(company_dir)

        companies_info.append({
            'name': company_name,
            'count': filing_count
        })

        if filing_count < 10:
            removed_companies.append((company_name, filing_count))
            print(f"刪除：{company_name} ({filing_count} 份年報)")
            # 刪除整個公司目錄
            try:
                shutil.rmtree(company_dir)
            except Exception as e:
                print(f"  錯誤：無法刪除 {company_name}：{e}")
        else:
            kept_companies.append((company_name, filing_count))
            print(f"保留：{company_name} ({filing_count} 份年報)")

    # 生成總結報告
    report_path = "總結.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# SEC Edgar 年報篩選總結\n\n")
        f.write(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 篩選標準\n\n")
        f.write("- 保留條件：至少有 **10份** 10-K年報\n")
        f.write("- 刪除條件：少於 10份 10-K年報\n\n")

        f.write("## 統計概覽\n\n")
        f.write(f"- 總公司數：**{len(companies_info)}**\n")
        f.write(f"- 保留公司數：**{len(kept_companies)}**\n")
        f.write(f"- 刪除公司數：**{len(removed_companies)}**\n\n")

        if kept_companies:
            f.write("## 保留的公司列表\n\n")
            f.write("| 公司代碼 | 年報數量 |\n")
            f.write("|---------|----------|\n")
            for name, count in sorted(kept_companies, key=lambda x: (-x[1], x[0])):
                f.write(f"| {name} | {count} |\n")
            f.write("\n")

        if removed_companies:
            f.write("## 刪除的公司列表\n\n")
            f.write("| 公司代碼 | 年報數量 |\n")
            f.write("|---------|----------|\n")
            for name, count in sorted(removed_companies, key=lambda x: (-x[1], x[0])):
                f.write(f"| {name} | {count} |\n")
            f.write("\n")

        f.write("## 年報數量分佈\n\n")

        # 統計年報數量分佈
        distribution = {}
        for info in companies_info:
            count = info['count']
            distribution[count] = distribution.get(count, 0) + 1

        f.write("| 年報數量 | 公司數量 |\n")
        f.write("|---------|----------|\n")
        for count in sorted(distribution.keys(), reverse=True):
            f.write(f"| {count} | {distribution[count]} |\n")

    print(f"\n總結報告已生成：{report_path}")
    print(f"\n處理完成！")
    print(f"  - 掃描公司總數：{len(companies_info)}")
    print(f"  - 保留公司數：{len(kept_companies)}")
    print(f"  - 刪除公司數：{len(removed_companies)}")

if __name__ == "__main__":
    main()
