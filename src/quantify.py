#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
數位韌性量化模組 - 六維度韌性能力框架
- 基於數位韌性理論的 6 個核心能力
- 每個能力由獨立的 LLM Agent 評分
- Absorb, Adopt, Transform, Anticipate, Rebound, Learn
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import time

try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError(
        "llama-cpp-python 未安裝。請執行: uv pip install llama-cpp-python"
    )

from .utils import setup_logger, Config

logger = setup_logger(__name__)

# --------------------------------
# 模型配置
# --------------------------------
MODEL_PATH = Config.PROJECT_ROOT / "models" / "gpt-oss-20b-Q4_0.gguf"

DEFAULT_LLM_PARAMS = {
    "n_ctx": 49152,      # 48K context for Q4 model (conservative for 24GB GPU - 80.5% utilization, safer for large prompts)
    "n_gpu_layers": -1,
    "n_threads": 8,
    "verbose": False,
}

DEFAULT_GEN_PARAMS = {
    "temperature": 0.1,
    "max_tokens": 1500,
    "stop": ["}```", "\n\n\n"],
}

# --------------------------------
# Agent 章節分配配置
# --------------------------------
# 每個 Agent 只讀取與其韌性能力相關的章節
# 彈性配置：根據各 Agent 的實際需求設定不同上限

AGENT_SECTION_MAPPING = {
    "absorb": [
        "item_1a",            # 風險因素（供應鏈、災害、系統中斷）- 高優先級
        "item_9a",            # Controls & Procedures - 高優先級
        "item_1c",            # Cybersecurity - 高優先級
        "cybersecurity",      # 額外資安段落（如果有）
        "information_security", # Information Security（如果有）
    ],
    "adopt": [
        "item_7",             # MD&A（管理層如何應對市場與衝擊）- 高優先級
        "item_1",             # Business（策略與營運模式）- 中優先級
        "item_1a",            # 部分風險應對內容 - 低優先級
    ],
    "transform": [
        "item_7",             # MD&A（轉型計劃）- 高優先級
        "item_1",             # Business（商業模式變革）- 高優先級
        "esg_sustainability", # ESG/淨零/數位轉型 - 中優先級
    ],
    "anticipate": [
        "item_1a",            # 風險識別、情境說明 - 高優先級
        "item_1c",            # 資安風險監測、評估 - 高優先級
        "cybersecurity",      # 威脅情報、監控 - 中優先級
        "item_9a",            # ERM、持續監控 - 中優先級
    ],
    "rebound": [
        "item_1c",            # Incident response, logging, escalation - 高優先級
        "cybersecurity",      # 事件響應計劃 - 高優先級
        "item_9a",            # Disclosure controls, remediation - 中優先級
        "item_7",             # 過去衝擊與恢復 - 低優先級
    ],
    "learn": [
        "esg_sustainability", # 員工訓練、組織文化 - 高優先級
        "item_9a",            # Internal audit、改進 - 高優先級
        "item_1a",            # 過去經驗與調整 - 中優先級
    ],
}

# 每個 Agent 的最大 token 數（單 Agent 執行模式 - 實用配置）
# 基於 n_ctx=48K 與單 Agent 執行模式（每次只載入一個 Agent）：
# - Q4 模型 (~11GB) + 48K context 實測穩定（80.5% GPU 使用率）
# - 單 Agent 模式：每個 Agent 執行時獨立載入/卸載模型，無 KV cache 累積問題
# - 實測發現：需預留足夠空間給生成與 CUDA 緩衝
# - 保守設定 45K 為上限（預留 3K 給生成，確保穩定）
#
# 各 Agent 統計（最小/平均/最大 tokens）：
# - adopt:       25K / 54K / 76K → 設定 45K（90% 案例完整保留，大型案例損失 41%）
# - learn:       18K / 33K / 69K → 設定 45K（95% 案例完整保留，大型案例損失 35%）
# - absorb:      19K / 32K / 59K → 設定 45K（85% 案例完整保留，大型案例損失 24%）
# - anticipate:  19K / 32K / 59K → 設定 45K（85% 案例完整保留）
# - transform:    8K / 29K / 54K → 設定 45K（95% 案例完整保留，大型案例損失 17%）
# - rebound:      2K / 11K / 25K → 設定 45K（100% 案例完整保留）
MAX_TOKENS_PER_AGENT = {
    "absorb": 45000,      # 單 Agent 模式 - 大幅減少截斷
    "adopt": 45000,       # 單 Agent 模式 - 大幅減少截斷
    "transform": 45000,   # 單 Agent 模式 - 大幅減少截斷
    "anticipate": 45000,  # 單 Agent 模式 - 大幅減少截斷
    "rebound": 45000,     # 單 Agent 模式 - 大幅減少截斷
    "learn": 45000,       # 單 Agent 模式 - 大幅減少截斷
}

# 預設值（向後相容）
DEFAULT_MAX_TOKENS = 12000

# --------------------------------
# 數據結構
# --------------------------------
@dataclass
class DimensionScore:
    """單一韌性能力評分"""
    dimension: str  # absorb, adopt, transform, anticipate, rebound, learn
    score: float  # 0-100
    confidence: int  # 0=缺乏信心, 1=適度信心, 2=強烈信心
    evidence: List[str]  # 從 10-K 逐字引用的證據
    reasoning: str  # 為什麼這些證據代表該能力

@dataclass
class ResilienceScore:
    """數位韌性評分 - 六維度框架"""
    company: str
    year: int
    cik: Optional[str] = None

    # 六大韌性能力
    absorb: Optional[DimensionScore] = None          # 吸收衝擊能力
    adopt: Optional[DimensionScore] = None           # 適應衝擊能力
    transform: Optional[DimensionScore] = None       # 轉換衝擊能力
    anticipate: Optional[DimensionScore] = None      # 預測能力
    rebound: Optional[DimensionScore] = None         # 反彈能力
    learn: Optional[DimensionScore] = None           # 學習能力

    # 整體分數
    overall_score: float = 0.0
    overall_confidence: float = 0.0

    # 元數據
    agent_version: str = "1.0"
    processing_time: float = 0.0
    timestamp: str = ""

    def calculate_overall(self):
        """計算整體分數（6個維度加權平均）"""
        # 可以選擇等權重或加權
        weights = {
            "absorb": 1/6,
            "adopt": 1/6,
            "transform": 1/6,
            "anticipate": 1/6,
            "rebound": 1/6,
            "learn": 1/6,
        }

        total_score = 0.0
        total_confidence = 0.0
        count = 0

        for dim_name, weight in weights.items():
            dim_score = getattr(self, dim_name)
            if dim_score and dim_score.score is not None:
                total_score += dim_score.score * weight
                total_confidence += dim_score.confidence * weight
                count += 1

        if count > 0:
            self.overall_score = round(total_score, 2)
            # Average confidence (0-2 scale)
            self.overall_confidence = round(total_confidence, 2)

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)

# --------------------------------
# LLM 包裝器
# --------------------------------
class LLMWrapper:
    """LLM 包裝器"""

    def __init__(self, model_path: Optional[Path] = None, llm_params: Optional[Dict] = None):
        self.model_path = model_path or MODEL_PATH
        self.llm_params = {**DEFAULT_LLM_PARAMS, **(llm_params or {})}
        self.llm: Optional[Llama] = None

    def load_model(self) -> bool:
        """載入模型"""
        if self.llm is not None:
            logger.info("模型已載入")
            return True

        try:
            logger.info(f"正在載入模型: {self.model_path}")
            logger.info(f"LLM 參數: {self.llm_params}")
            start_time = time.time()

            self.llm = Llama(
                model_path=str(self.model_path),
                **self.llm_params
            )

            load_time = time.time() - start_time
            logger.info(f"✅ 模型載入成功 (耗時 {load_time:.2f}s)")
            return True

        except Exception as e:
            logger.error(f"模型載入失敗: {e}")
            return False

    def generate(self, prompt: str, override_params: Optional[Dict] = None) -> str:
        """生成回應"""
        if self.llm is None:
            raise RuntimeError("模型尚未載入，請先呼叫 load_model()")

        params = {**DEFAULT_GEN_PARAMS, **(override_params or {})}

        try:
            response = self.llm(prompt, **params)
            return response['choices'][0]['text']
        except Exception as e:
            logger.error(f"生成失敗: {e}")
            raise

    def reset_cache(self):
        """清空 KV cache（用於大型 Agent 執行前，避免記憶體累積）"""
        if self.llm is None:
            logger.warning("模型尚未載入，無法清空 cache")
            return

        try:
            self.llm.reset()
            logger.info("🔄 KV cache 已清空")
        except Exception as e:
            logger.error(f"清空 KV cache 失敗: {e}")

    def unload_model(self):
        """卸載模型"""
        if self.llm:
            del self.llm
            self.llm = None
        logger.info("模型已卸載")

# --------------------------------
# 六個韌性能力的 System Prompts
# --------------------------------

def load_prompt(name: str) -> str:
    """從 src/prompts 載入 System Prompt"""
    try:
        prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / f"{name}.txt"
        if not prompt_path.exists():
            logger.error(f"Prompt 檔案不存在: {prompt_path}")
            return ""
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"載入 Prompt {name} 失敗: {e}")
        return ""

SYSTEM_PROMPT_ABSORB = load_prompt("absorb")

SYSTEM_PROMPT_ADOPT = load_prompt("adopt")

SYSTEM_PROMPT_TRANSFORM = load_prompt("transform")

SYSTEM_PROMPT_ANTICIPATE = load_prompt("anticipate")

SYSTEM_PROMPT_REBOUND = load_prompt("rebound")

SYSTEM_PROMPT_LEARN = load_prompt("learn")

# --------------------------------
# Helper Functions
# --------------------------------

def load_cleaned_report(company: str, year: int) -> Optional[Dict[str, str]]:
    """載入已清理的 10-K 報告"""
    year_short = str(year)[-2:]

    patterns = [
        f"{company.upper()}_10-K_*-{year_short}-*_primary-document.json",
        f"{company}_10-K_*-{year_short}-*_primary-document.json",
    ]

    for pattern in patterns:
        matches = list(Config.CLEANED_DATA_DIR.glob(pattern))
        if matches:
            json_path = sorted(matches)[-1]
            logger.info(f"找到報告: {json_path.name}")

            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                return data
            except Exception as e:
                logger.error(f"讀取報告失敗 {json_path}: {e}")
                return None

    logger.warning(f"找不到報告: {company} {year}")
    return None

def prepare_report_context(report_data: Dict[str, str]) -> str:
    """準備報告上下文（已棄用 - 請使用 extract_relevant_sections）"""
    sections = []

    for key, value in report_data.items():
        if key not in ["source", "company", "year", "cik"] and value:
            sections.append(f"## {key.upper()}\n{value}\n")

    return "\n".join(sections)

def extract_relevant_sections(
    report_data: Dict[str, str],
    agent_name: str,
    max_tokens: Optional[int] = None
) -> str:
    """
    為特定 Agent 提取相關章節

    Args:
        report_data: 完整報告數據（字典）
        agent_name: Agent 名稱 (absorb/adopt/transform/anticipate/rebound/learn)
        max_tokens: 最大 token 數限制（None 則使用該 Agent 的預設值）

    Returns:
        組合後的相關章節文本（控制在 max_tokens 內）
    """
    # 獲取該 Agent 的章節列表
    sections = AGENT_SECTION_MAPPING.get(agent_name, [])

    # 獲取該 Agent 的 token 限制（支援字典配置）
    if max_tokens is None:
        if isinstance(MAX_TOKENS_PER_AGENT, dict):
            max_tokens = MAX_TOKENS_PER_AGENT.get(agent_name, DEFAULT_MAX_TOKENS)
        else:
            max_tokens = MAX_TOKENS_PER_AGENT

    if not sections:
        logger.warning(f"未找到 {agent_name} 的章節映射，返回空字串")
        return ""

    context_parts = []
    total_chars = 0
    max_chars = max_tokens * 4  # 粗估 1 token ≈ 4 chars

    for section_key in sections:
        # 檢查章節是否存在且非空
        if section_key in report_data and report_data[section_key]:
            section_text = report_data[section_key]
            section_header = f"\n\n=== {section_key.upper()} ===\n\n"

            # 檢查是否超出限制
            potential_total = total_chars + len(section_header) + len(section_text)

            if potential_total > max_chars:
                # 計算剩餘可用空間
                remaining_space = max_chars - total_chars - len(section_header)

                if remaining_space > 1000:  # 至少保留 1000 字元
                    # 截斷章節
                    section_text = section_text[:remaining_space] + "\n\n[...內容已截斷]"
                    context_parts.append(section_header + section_text)
                    total_chars += len(section_header) + len(section_text)
                    logger.info(f"  {section_key}: 已截斷至 {remaining_space} 字元")
                else:
                    # 空間不足，停止添加
                    logger.info(f"  {section_key}: 空間不足，跳過")
                break

            # 添加完整章節
            context_parts.append(section_header + section_text)
            total_chars += len(section_header) + len(section_text)
            logger.info(f"  {section_key}: {len(section_text)} 字元")

    # 記錄總計
    total_tokens_approx = total_chars / 4
    logger.info(f"✅ {agent_name} 上下文: {total_chars:,} 字元 (~{total_tokens_approx:.0f} tokens)")

    return "".join(context_parts)

def parse_json_response(response: str) -> Optional[Dict]:
    """解析 JSON 回應"""
    # 直接解析
    try:
        return json.loads(response)
    except:
        pass

    # 提取 JSON code block
    json_match = re.search(r'```json\s*(\\{.*?\\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass

    # 提取 {...}
    json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass

    logger.error("無法解析 JSON")
    return None

# --------------------------------
# 六個獨立的 Agent 評分函數
# --------------------------------

def agent_absorb(
    llm_wrapper: LLMWrapper,
    company: str,
    year: int,
    report_data: Dict[str, str]
) -> Optional[DimensionScore]:
    """Absorb Agent - 評估吸收衝擊能力（只讀取相關章節）"""
    logger.info(f"=== Absorb Agent 評分: {company} ({year}) ===")

    # 提取相關章節：item_1a, item_9a, item_1c, cybersecurity, information_security
    relevant_context = extract_relevant_sections(report_data, "absorb")

    if not relevant_context:
        logger.warning("Absorb Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_ABSORB}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the ABSORB capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(
            prompt,
            override_params={
                "temperature": 0.1,
                "max_tokens": 1500,
                "stop": ["}```", "\n\n\n"],
            }
        )

        logger.info(f"Absorb 回應長度: {len(response)} 字元")
        logger.info(f"Absorb 回應前 500 字: {response[:500]}")
        logger.info(f"Absorb 回應後 500 字: {response[-500:]}")

        result = parse_json_response(response)
        if not result:
            logger.error("Absorb Agent JSON 解析失敗")
            logger.error(f"完整回應:\n{response}")
            return None

        return DimensionScore(
            dimension="absorb",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )

    except Exception as e:
        logger.error(f"Absorb Agent 失敗: {e}")
        return None

def agent_adopt(llm_wrapper: LLMWrapper, company: str, year: int, report_data: Dict[str, str]) -> Optional[DimensionScore]:
    """Adopt Agent - 評估適應衝擊能力"""
    logger.info(f"=== Adopt Agent 評分: {company} ({year}) ===")

    # 提取相關章節：item_7, item_1, item_1a
    relevant_context = extract_relevant_sections(report_data, "adopt")

    if not relevant_context:
        logger.warning("Adopt Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_ADOPT}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the ADOPT capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(prompt, override_params={"temperature": 0.1, "max_tokens": 2048})
        result = parse_json_response(response)
        if not result:
            return None

        return DimensionScore(
            dimension="adopt",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Adopt Agent 失敗: {e}")
        return None

def agent_transform(llm_wrapper: LLMWrapper, company: str, year: int, report_data: Dict[str, str]) -> Optional[DimensionScore]:
    """Transform Agent - 評估轉換衝擊能力"""
    logger.info(f"=== Transform Agent 評分: {company} ({year}) ===")

    # 提取相關章節：item_7, item_1, esg_sustainability
    relevant_context = extract_relevant_sections(report_data, "transform")

    if not relevant_context:
        logger.warning("Transform Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_TRANSFORM}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the TRANSFORM capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(prompt, override_params={"temperature": 0.1, "max_tokens": 2048})
        result = parse_json_response(response)
        if not result:
            return None

        return DimensionScore(
            dimension="transform",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Transform Agent 失敗: {e}")
        return None

def agent_anticipate(llm_wrapper: LLMWrapper, company: str, year: int, report_data: Dict[str, str]) -> Optional[DimensionScore]:
    """Anticipate Agent - 評估預測能力"""
    logger.info(f"=== Anticipate Agent 評分: {company} ({year}) ===")

    # 提取相關章節：item_1a, item_1c, cybersecurity, item_9a
    relevant_context = extract_relevant_sections(report_data, "anticipate")

    if not relevant_context:
        logger.warning("Anticipate Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_ANTICIPATE}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the ANTICIPATE capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(prompt, override_params={"temperature": 0.1, "max_tokens": 2048})
        result = parse_json_response(response)
        if not result:
            return None

        return DimensionScore(
            dimension="anticipate",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Anticipate Agent 失敗: {e}")
        return None

def agent_rebound(llm_wrapper: LLMWrapper, company: str, year: int, report_data: Dict[str, str]) -> Optional[DimensionScore]:
    """Rebound Agent - 評估反彈能力"""
    logger.info(f"=== Rebound Agent 評分: {company} ({year}) ===")

    # 提取相關章節：item_1c, cybersecurity, item_9a, item_7
    relevant_context = extract_relevant_sections(report_data, "rebound")

    if not relevant_context:
        logger.warning("Rebound Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_REBOUND}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the REBOUND capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(prompt, override_params={"temperature": 0.1, "max_tokens": 2048})
        result = parse_json_response(response)
        if not result:
            return None

        return DimensionScore(
            dimension="rebound",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Rebound Agent 失敗: {e}")
        return None

def agent_learn(llm_wrapper: LLMWrapper, company: str, year: int, report_data: Dict[str, str]) -> Optional[DimensionScore]:
    """Learn Agent - 評估學習能力"""
    logger.info(f"=== Learn Agent 評分: {company} ({year}) ===")

    # 提取相關章節：esg_sustainability, item_9a, item_1a
    relevant_context = extract_relevant_sections(report_data, "learn")

    if not relevant_context:
        logger.warning("Learn Agent: 無相關章節，返回 None")
        return None

    prompt = f"""{SYSTEM_PROMPT_LEARN}

# Company: {company} ({year})

## 10-K Report Content (Relevant Sections):

{relevant_context}

---

Now evaluate the LEARN capability and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(prompt, override_params={"temperature": 0.1, "max_tokens": 2048})
        result = parse_json_response(response)
        if not result:
            return None

        return DimensionScore(
            dimension="learn",
            score=float(result.get("score", 0)),
            confidence=int(result.get("confidence", 0)),
            evidence=result.get("evidence", []),
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        logger.error(f"Learn Agent 失敗: {e}")
        return None

# --------------------------------
# 主評分函數
# --------------------------------

def score_resilience(
    llm_wrapper: LLMWrapper,
    company: str,
    year: int,
    report_data: Dict[str, str]
) -> Optional[ResilienceScore]:
    """
    使用 6 個獨立 Agent 評估數位韌性

    Args:
        llm_wrapper: LLM 實例（已載入）
        company: 公司名稱
        year: 年份
        report_data: 報告數據

    Returns:
        ResilienceScore 物件
    """
    logger.info(f"=== 開始評分: {company} ({year}) ===")
    start_time = time.time()

    # 初始化結果
    score_obj = ResilienceScore(
        company=company,
        year=year,
        cik=report_data.get("cik"),
        agent_version="3.0",  # 單 Agent 執行模式（完全隔離，無截斷）
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    )

    # 單 Agent 執行模式：每個 Agent 獨立載入/卸載模型
    # 優點：
    # 1. 每個 Agent 都能使用完整 64K context（幾乎無截斷）
    # 2. 無 KV cache 累積問題（每次重新載入模型）
    # 3. GPU 記憶體穩定（不會因多個 Agent 累積而 OOM）
    #
    # 成本：
    # - 6 次模型載入/卸載（每次 ~1.5s，總共 ~9s）
    # - 總處理時間增加約 10-20%
    #
    # Trade-off: 時間換質量（無截斷 vs 略慢）

    agent_functions = [
        ("absorb", agent_absorb),
        ("adopt", agent_adopt),
        ("transform", agent_transform),
        ("anticipate", agent_anticipate),
        ("rebound", agent_rebound),
        ("learn", agent_learn),
    ]

    for agent_name, agent_func in agent_functions:
        logger.info(f"🔄 執行 {agent_name.upper()} Agent（單獨載入模型）")

        # 1. 載入模型（每個 Agent 獨立載入）
        if not llm_wrapper.load_model():
            logger.error(f"❌ {agent_name} Agent 模型載入失敗")
            setattr(score_obj, agent_name, None)
            continue

        # 2. 執行 Agent
        try:
            result = agent_func(llm_wrapper, company, year, report_data)
            setattr(score_obj, agent_name, result)
        except Exception as e:
            logger.error(f"❌ {agent_name} Agent 執行失敗: {e}")
            setattr(score_obj, agent_name, None)

        # 3. 卸載模型（釋放 GPU 記憶體）
        llm_wrapper.unload_model()

    # 計算整體分數
    score_obj.calculate_overall()

    # 記錄處理時間
    score_obj.processing_time = time.time() - start_time

    logger.info(f"✅ 評分完成: {score_obj.overall_score:.1f}/100 (耗時 {score_obj.processing_time:.1f}s)")

    return score_obj

def save_score_to_file(score: ResilienceScore, output_dir: Optional[Path] = None) -> Path:
    """儲存評分結果"""
    out_dir = output_dir or Config.SCORES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{score.company}_{score.year}_score.json"
    output_path = out_dir / filename

    output_path.write_text(
        json.dumps(score.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info(f"評分已儲存: {output_path}")
    return output_path

# --------------------------------
# 測試函數
# --------------------------------


# --------------------------------
# 評分員 Agent (Reviewer)
# --------------------------------

@dataclass
class ReviewResult:
    """評分員審核結果"""
    dimension: str
    original_score: float
    original_confidence: int
    is_reasonable: bool  # 評分是否合理
    suggested_adjustments: str  # 建議調整
    review_confidence: int  # 審核者的信心 (0-2)

SYSTEM_PROMPT_REVIEWER = """You are a **Quality Assurance Analyst** reviewing digital resilience scores.

## Your Task
Review the scoring for a specific resilience capability and determine if:
1. The score (0-100) is justified by the evidence
2. The confidence level (0-2) is appropriate
3. The reasoning is logical

## Scoring Guidelines
- **Evidence-Score Match**: Does evidence support the score?
  - Strong evidence + high score = reasonable
  - Weak evidence + high score = unreasonable
  - No evidence + low score = reasonable

- **Confidence Level Check**:
  - 0 (缺乏): Should have empty evidence list
  - 1 (適度): Should have 2-5 pieces of evidence, some uncertainty
  - 2 (強烈): Should have 4+ pieces of strong evidence, clear patterns

## Output Format (JSON ONLY):
{
  "is_reasonable": true,
  "suggested_adjustments": "Brief suggestion or 'None' if reasonable",
  "review_confidence": 2
}

### CRITICAL RULES:
- If score > 70 but evidence < 3 items → is_reasonable = false
- If confidence = 2 but evidence < 4 items → is_reasonable = false
- If confidence = 0 but evidence exists → is_reasonable = false
- Output ONLY JSON, NO explanatory text

Start with { and end with }."""

def agent_reviewer(
    llm_wrapper: LLMWrapper,
    dimension_name: str,
    dimension_score: DimensionScore,
    report_context: str
) -> Optional[ReviewResult]:
    """評分員 Agent - 審核單一維度的評分"""
    logger.info(f"=== Reviewer Agent: {dimension_name} ===")

    prompt = f"""{SYSTEM_PROMPT_REVIEWER}

## Dimension: {dimension_name.upper()}

## Original Scoring:
- Score: {dimension_score.score}/100
- Confidence: {dimension_score.confidence} ({['缺乏', '適度', '強烈'][dimension_score.confidence]})
- Evidence Count: {len(dimension_score.evidence)}
- Evidence: {dimension_score.evidence[:3]}  # First 3 pieces
- Reasoning: {dimension_score.reasoning}

## Relevant Report Context (for verification):
{report_context[:5000]}

---

Review this scoring and output JSON:<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    try:
        response = llm_wrapper.generate(
            prompt,
            override_params={
                "temperature": 0.1,
                "max_tokens": 800,
                "stop": ["}```", "\n\n\n"],
            }
        )

        result = parse_json_response(response)
        if not result:
            logger.warning(f"Reviewer Agent failed for {dimension_name}")
            return None

        return ReviewResult(
            dimension=dimension_name,
            original_score=dimension_score.score,
            original_confidence=dimension_score.confidence,
            is_reasonable=result.get("is_reasonable", True),
            suggested_adjustments=result.get("suggested_adjustments", "None"),
            review_confidence=int(result.get("review_confidence", 1))
        )

    except Exception as e:
        logger.error(f"Reviewer Agent error for {dimension_name}: {e}")
        return None


def review_all_scores(
    llm_wrapper: LLMWrapper,
    score: ResilienceScore,
    report_context: str
) -> Dict[str, ReviewResult]:
    """審核所有維度的評分"""
    logger.info("\n=== 開始評分員審核 ===")
    reviews = {}

    dimensions = [
        ("absorb", score.absorb),
        ("adopt", score.adopt),
        ("transform", score.transform),
        ("anticipate", score.anticipate),
        ("rebound", score.rebound),
        ("learn", score.learn),
    ]

    for dim_name, dim_score in dimensions:
        if dim_score:
            review = agent_reviewer(llm_wrapper, dim_name, dim_score, report_context)
            if review:
                reviews[dim_name] = review

                # Log review result
                status = "✅ 合理" if review.is_reasonable else "⚠️ 需調整"
                logger.info(f"  {dim_name}: {status} - {review.suggested_adjustments}")

    logger.info(f"\n審核完成: {len(reviews)}/6 維度")
    return reviews


def test_scoring():
    """測試評分系統"""
    company = "AAPL"
    year = 2024

    logger.info("=== 測試六維度韌性評分 ===")

    # 載入報告
    report_data = load_cleaned_report(company, year)
    if not report_data:
        logger.error("報告載入失敗")
        return False

    # 初始化 LLM wrapper（不載入模型，由 score_resilience 內部的每個 Agent 獨立載入）
    wrapper = LLMWrapper()

    try:
        # 執行評分（單 Agent 模式：每個 Agent 獨立載入/卸載模型）
        score = score_resilience(wrapper, company, year, report_data)

        if score:
            # 載入模型給評分員審核使用
            if not wrapper.load_model():
                logger.error("LLM 載入失敗（評分員）")
                return False

            # 執行評分員審核
            report_context = prepare_report_context(report_data)
            reviews = review_all_scores(wrapper, score, report_context)

            logger.info("\n=== 評分結果 ===")
            logger.info(f"公司: {score.company} ({score.year})")
            logger.info(f"整體分數: {score.overall_score:.1f}/100")
            logger.info(f"整體信心: {score.overall_confidence:.2f} (平均值: 0=缺乏, 1=適度, 2=強烈)")
            logger.info(f"\n六維度分數:")

            # Helper function to display dimension safely
            def display_dim(name_zh, name_en, dim_score):
                if dim_score:
                    conf_label = {0: "缺乏", 1: "適度", 2: "強烈"}[dim_score.confidence]
                    logger.info(f"  - {name_en} ({name_zh}): {dim_score.score:.1f} (信心: {conf_label})")
                else:
                    logger.info(f"  - {name_en} ({name_zh}): N/A (評分失敗)")

            display_dim("吸收", "Absorb", score.absorb)
            display_dim("適應", "Adopt", score.adopt)
            display_dim("轉換", "Transform", score.transform)
            display_dim("預測", "Anticipate", score.anticipate)
            display_dim("反彈", "Rebound", score.rebound)
            display_dim("學習", "Learn", score.learn)

            # 顯示審核摘要
            if reviews:
                logger.info("\n=== 評分員審核摘要 ===")
                reasonable_count = sum(1 for r in reviews.values() if r.is_reasonable)
                logger.info(f"總審核: {len(reviews)}/6 維度")
                logger.info(f"合理評分: {reasonable_count}/{len(reviews)} 維度")

                # 顯示需調整的維度
                needs_adjustment = [dim for dim, r in reviews.items() if not r.is_reasonable]
                if needs_adjustment:
                    logger.info("\n⚠️ 需調整維度:")
                    for dim in needs_adjustment:
                        r = reviews[dim]
                        logger.info(f"  - {dim}: {r.suggested_adjustments}")
                else:
                    logger.info("\n✅ 所有維度評分合理")

            # 儲存結果
            output_path = save_score_to_file(score)
            logger.info(f"\n結果已儲存至: {output_path}")

            logger.info("✅ 評分測試成功")
            return True
        else:
            logger.error("評分失敗")
            return False

    finally:
        wrapper.unload_model()

if __name__ == "__main__":
    test_scoring()

# --------------------------------
# 向後相容層 (Backward Compatibility)
# --------------------------------
def agent1_score_report(
    llm_wrapper: LLMWrapper,
    company: str,
    year: int,
    report_data: Dict[str, str]
) -> Optional[ResilienceScore]:
    """
    向後相容函數 - 對應 v1.0 的 agent1_score_report
    實際調用 score_resilience
    """
    return score_resilience(llm_wrapper, company, year, report_data)

