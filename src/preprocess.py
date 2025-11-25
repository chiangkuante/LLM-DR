#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
10-K 報告前處理模組
- 提取關鍵章節（Item 1, 1A, 1C, 7, 7A, 9A, Cybersecurity, ESG）
- 清理 HTML 並輸出 JSON
- 支援批次處理與進度追蹤
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from tqdm import tqdm

# 匯入專案工具
from utils import setup_logger, Config

# 設置 logger
logger = setup_logger(__name__)

# --------------------------------
# 使用 Config 管理路徑
# --------------------------------
IN_ROOT = Config.RAW_DATA_DIR
OUT_DIR = Config.CLEANED_DATA_DIR

# -----------------------------
# 精準 Item 抬頭（目標）
# 先長再短；1/7 後面禁止接數字或字母，避免 10/12/7B
# -----------------------------
TARGET_ITEM_RE = re.compile(
    r"""(?imx)
    ^\s*
    item\s+
    (?P<num>
        (?:1A|1C|7A|9A) | (?:1(?![0-9A-Za-z])) | (?:7(?![0-9A-Za-z]))
    )
    \s*(?:[\.\-:)]\s*)?
    (?P<title>[^\n]{0,160})?
    $
    """
)

# -----------------------------
# 任何 Item 抬頭（作為切割邊界）
# Item 1 ~ Item 15（含 A/B 等字母）
# -----------------------------
ANY_ITEM_PATTERN = r"""
    ^\s*item\s+
    (?:
        [1-9] | 1[0-5]
    )
    [A-Za-z]?
    \s*(?:[\.\-:)]\s*)?
    [^\n]{0,160}$
"""

ANY_ITEM_RE = re.compile(ANY_ITEM_PATTERN, re.IGNORECASE | re.MULTILINE | re.VERBOSE)

# -----------------------------
# Generic 抬頭（Cybersecurity/InfoSec/ESG）
# 允許前綴短代號/破折號；允許合成標題（e.g., "Security and Technology Risks"）
# -----------------------------
GENERIC_PATTERNS = [
    r"(?:cyber\s*security|cybersecurity)\b",
    r"information\s+security\b",
    r"\bESG\b",
    r"sustainab(?:le|ility)\b",
    r"corporate\s+(?:sustainability|responsibility)\b",
    r"digital\s+trust\b",
    # 常見合成：把 "security" 與 "technology risks" 合體也抓一下
    r"(?:security\s+and\s+technology\s+risks)",
]

GENERIC_HEADER_PATTERN = r"""
    ^
    \s*
    (?:[A-Z0-9.\-–—]{0,12}\s+)?     # 容許短代號或破折號
    (?P<hdr>(?:%s))
    [^\n]{0,160}?$
""" % "|".join(GENERIC_PATTERNS)

GENERIC_HEADER_RE = re.compile(GENERIC_HEADER_PATTERN, re.IGNORECASE | re.MULTILINE | re.VERBOSE)

# 任一「邊界抬頭」= 任何 Item 或 Generic
# 直接組合 pattern 字串，不使用已編譯的 pattern
ANY_HEADER_RE = re.compile(
    r"(?:" + ANY_ITEM_PATTERN.strip() + r")|(?:" + GENERIC_HEADER_PATTERN.strip() + r")",
    re.IGNORECASE | re.MULTILINE | re.VERBOSE
)

TOC_HINT = re.compile(r"(?i)\btable of contents\b|\bindex\b")
DOT_LEADER = re.compile(r"\.{3,}\s*\d{1,3}\b")

SECTION_KEYS = {
    "1": "item_1",
    "1A": "item_1a",
    "1C": "item_1c",
    "7": "item_7",
    "7A": "item_7a",
    "9A": "item_9a",
    "CYBERSECURITY": "cybersecurity",
    "INFORMATION_SECURITY": "information_security",
    "ESG_SUSTAINABILITY": "esg_sustainability",
}

def html_to_text(html: str) -> str:
    """
    將 HTML 轉換為純文字

    Args:
        html: HTML 字符串

    Returns:
        清理後的純文字
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    # 以 \n 拼接，保留行首定位能力
    text = soup.get_text("\n")
    text = unicodedata.normalize("NFKC", text).replace("\r", "\n")
    text = re.sub(r"[ \t\u00A0]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()

def find_headers(text: str) -> Tuple[List[Tuple], List[Tuple]]:
    """
    尋找文本中的目標章節標題

    Args:
        text: 待分析的文本

    Returns:
        (headers, boundaries) 元組
    """
    headers = []

    # 目標 Items
    for m in TARGET_ITEM_RE.finditer(text):
        g = m.group("num").upper()
        if g in ["1", "1A", "1C", "7", "7A", "9A"]:
            headers.append((m.start(), m.end(), f"ITEM:{g}", m.group(0).strip()))

    # Generic 抬頭
    for m in GENERIC_HEADER_RE.finditer(text):
        hdr = m.group("hdr").lower()
        if "information security" in hdr:
            label = "GEN:INFORMATION_SECURITY"
        elif "cyber" in hdr and "security" in hdr:
            label = "GEN:CYBERSECURITY"
        elif ("esg" in hdr) or ("sustainab" in hdr) or ("corporate responsibility" in hdr):
            label = "GEN:ESG_SUSTAINABILITY"
        else:
            continue
        headers.append((m.start(), m.end(), label, m.group(0).strip()))

    # 切割邊界清單（包含所有 Items 與 Generic）
    boundaries = []
    for m in ANY_HEADER_RE.finditer(text):
        boundaries.append((m.start(), m.end()))

    headers.sort(key=lambda x: x[0])
    boundaries.sort(key=lambda x: x[0])
    return headers, boundaries

def next_boundary(boundaries: List[Tuple], cur_start: int) -> Optional[int]:
    """回傳在 cur_start 後的下一個邊界起點；找不到則回 None"""
    for s, e in boundaries:
        if s > cur_start:
            return s
    return None

def slice_section(text: str, start_idx: int, boundaries: List[Tuple], fallback_end: int) -> str:
    """切割章節文本"""
    end_idx = next_boundary(boundaries, start_idx)
    if end_idx is None:
        end_idx = fallback_end
    return text[start_idx:end_idx].strip()

def is_probably_toc(section: str) -> bool:
    """判斷是否為目錄"""
    if len(section) < 400:
        return True
    if TOC_HINT.search(section):
        return len(section) < 1200
    if DOT_LEADER.search(section) and len(section) < 2000:
        return True
    return False

def extract_sections(text: str) -> Dict[str, str]:
    """
    從文本中提取所有目標章節

    Args:
        text: 清理後的文本

    Returns:
        章節字典 {section_key: section_text}
    """
    headers, boundaries = find_headers(text)
    buckets = {
        "item_1": [],
        "item_1a": [],
        "item_1c": [],
        "item_7": [],
        "item_7a": [],
        "item_9a": [],
        "cybersecurity": [],
        "information_security": [],
        "esg_sustainability": [],
    }

    text_len = len(text)
    for (s, e, label, raw) in headers:
        section_text = slice_section(text, s, boundaries, text_len)
        if is_probably_toc(section_text):
            continue

        if label.startswith("ITEM:"):
            key = SECTION_KEYS[label.split(":")[1]]
        else:
            key = SECTION_KEYS.get(label.split(":")[1], None)

        if key:
            buckets[key].append(section_text)

    # 去重/取最長
    final_sections = {}
    for k, chunks in buckets.items():
        if not chunks:
            final_sections[k] = ""
        else:
            final_sections[k] = max(chunks, key=len).strip()
    return final_sections

def process_html_file(in_path: Path) -> Dict[str, str]:
    """
    處理單個 HTML 檔案

    Args:
        in_path: HTML 檔案路徑

    Returns:
        提取的章節字典
    """
    raw = in_path.read_text(encoding="utf-8", errors="ignore")
    text = html_to_text(raw)
    return extract_sections(text)

def iter_html_files(root: Path):
    """遞迴遍歷目錄尋找 HTML 檔案"""
    if root.is_file() and root.suffix.lower() == ".html":
        yield root
        return
    for p in root.rglob("*.html"):
        yield p

def save_json(rel_path: Path, sections: Dict[str, str]) -> Path:
    """
    儲存章節為 JSON

    Args:
        rel_path: 相對路徑（用於生成檔名）
        sections: 章節字典

    Returns:
        JSON 檔案路徑
    """
    payload = {"source_path": str(rel_path).replace(os.sep, "/"), **sections}
    stem_safe = "_".join(rel_path.with_suffix("").parts)
    json_path = OUT_DIR / f"{stem_safe}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path

def process_batch(input_root: Optional[Path] = None,
                  output_dir: Optional[Path] = None,
                  show_progress: bool = True) -> Dict[str, any]:
    """
    批次處理所有 HTML 檔案

    Args:
        input_root: 輸入目錄（預設使用 Config.RAW_DATA_DIR）
        output_dir: 輸出目錄（預設使用 Config.CLEANED_DATA_DIR）
        show_progress: 是否顯示進度條

    Returns:
        處理結果統計字典
    """
    in_root = input_root or IN_ROOT
    out_dir = output_dir or OUT_DIR

    logger.info(f"輸入目錄: {in_root}")
    logger.info(f"輸出目錄: {out_dir}")

    # 確保輸出目錄存在
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_root.exists():
        logger.error(f"輸入目錄不存在: {in_root}")
        return {"success": False, "error": "Input directory not found"}

    # 收集所有檔案
    files = list(iter_html_files(in_root))
    if not files:
        logger.warning(f"未找到 HTML 檔案: {in_root}")
        return {"success": False, "error": "No HTML files found"}

    logger.info(f"找到 {len(files)} 個 HTML 檔案")

    # 處理統計
    stats = {
        "total": len(files),
        "processed": 0,
        "failed": 0,
        "success": True,
        "files": []
    }

    # 使用 tqdm 顯示進度
    iterator = tqdm(files, desc="處理 10-K 報告") if show_progress else files

    for f in iterator:
        try:
            rel = f.relative_to(in_root)
            sections = process_html_file(f)

            # 暫時使用全局 OUT_DIR（待修正）
            outp = save_json(rel, sections)

            logger.debug(f"成功: {rel} -> {outp.name}")
            stats["processed"] += 1
            stats["files"].append({
                "source": str(rel),
                "output": outp.name,
                "status": "success"
            })
        except Exception as e:
            logger.error(f"處理失敗 {f}: {e}")
            stats["failed"] += 1
            stats["files"].append({
                "source": str(f),
                "error": str(e),
                "status": "failed"
            })

    logger.info(f"處理完成: {stats['processed']} 成功, {stats['failed']} 失敗")
    return stats

def main():
    """命令行入口"""
    logger.info(f"輸入目錄: {IN_ROOT}")
    logger.info(f"輸出目錄: {OUT_DIR}")

    if not IN_ROOT.exists():
        logger.error(f"輸入目錄不存在: {IN_ROOT}")
        sys.exit(1)

    stats = process_batch(show_progress=True)

    if stats["success"]:
        logger.info(f"✅ 處理完成: {stats['processed']}/{stats['total']} 個檔案")
    else:
        logger.error(f"❌ 處理失敗: {stats.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
