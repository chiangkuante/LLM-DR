"""
Utility functions for logging, configuration, and common operations.
"""

import logging
from pathlib import Path
from typing import Optional
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    設置 logger 用於追蹤處理進度

    Args:
        name: Logger 名稱
        level: Logging 層級

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 如果已有 handler，不重複添加
    if logger.handlers:
        return logger

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


class Config:
    """
    專案設定管理
    """
    # 專案根目錄
    PROJECT_ROOT = Path(__file__).parent.parent

    # 資料目錄
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_DIR = DATA_DIR / "10k_raw"
    CLEANED_DATA_DIR = DATA_DIR / "10k_cleaned"
    SCORES_DIR = DATA_DIR / "scores"
    TRENDS_DIR = DATA_DIR / "trends"

    # 模型目錄
    MODELS_DIR = PROJECT_ROOT / "models"
    MODEL_PATH = MODELS_DIR / "gpt-oss-20b-Q8_0.gguf"

    # Notebook 目錄
    NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

    @classmethod
    def ensure_directories(cls):
        """確保所有必要目錄存在"""
        for dir_path in [
            cls.DATA_DIR,
            cls.RAW_DATA_DIR,
            cls.CLEANED_DATA_DIR,
            cls.SCORES_DIR,
            cls.TRENDS_DIR,
            cls.MODELS_DIR,
            cls.NOTEBOOKS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


def get_project_root() -> Path:
    """取得專案根目錄"""
    return Config.PROJECT_ROOT


def format_file_size(size_bytes: int) -> str:
    """
    格式化檔案大小

    Args:
        size_bytes: 檔案大小（bytes）

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
