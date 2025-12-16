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
import os

try:
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "openai 未安裝。請執行: uv pip install openai"
    )

from .utils import setup_logger, Config
from .agent_utils import run_agent1_with_retry, parse_json_response

logger = setup_logger(__name__)

# --------------------------------
# 模型配置
# --------------------------------
# 注意: 模型路徑與參數現在由 llama-server 啟動腳本 (src/tools/launch_server.sh) 控制。
# Python 端不再負責載入模型，僅負責與 Server 通訊。

# DEFAULT_LLM_PARAMS 已廢棄 (由 Server 端參數決定)

DEFAULT_GEN_PARAMS = {
    "temperature": 0.1,
    "max_tokens": 2000,
    "stop": ["}```", "\n\n\n"],
}

# 關鍵參數: 控制輸入 Prompt 的長度，避免超過 Server 的 Context Window (例如 32k)
# 建議設定為: Server Context - Max Output - Buffer
# 32768 - 1000 - 1000 ~= 30000 (這裡設定 28000 保守一點)
MAX_TOKENS_PER_AGENT = 64000

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

# --------------------------------
# 數據結構
# --------------------------------
@dataclass
class ReviewResult:
    """評分員審核結果"""
    dimension: str
    original_score: float
    # original_confidence: int # Removed/Ignored in new prompt logic, but let's keep it clean or just optional
    # New prompt structure: status, final_score, final_reasoning, audit_note
    status: str # APPROVED | CORRECTED
    final_score: float
    final_reasoning: str
    audit_note: str
    
    # Legacy fields for compatibility if needed, or remove them. 
    # The existing code expects 'is_reasonable'. Let's map 'status' to it.
    @property
    def is_reasonable(self) -> bool:
        return self.status == "APPROVED"

    @property # Compatible alias
    def suggested_adjustments(self) -> str:
        return self.audit_note

    @property # Compatible alias
    def suggested_adjustments(self) -> str:
        return self.audit_note
@dataclass
class DimensionScore:
    """單一韌性能力評分"""
    dimension: str  # absorb, adopt, transform, anticipate, rebound, learn
    score: float  # 0-100
    evidence: List[str]  # 從 10-K 逐字引用的證據
    reasoning: str  # 為什麼這些證據代表該能力
    review: Optional['ReviewResult'] = None  # 評分員審核結果

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
        count = 0

        for dim_name, weight in weights.items():
            dim_score = getattr(self, dim_name)
            if dim_score and dim_score.score is not None:
                total_score += dim_score.score * weight
                count += 1

        if count > 0:
            self.overall_score = round(total_score, 2)

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)

# --------------------------------
# LLM 包裝器
# --------------------------------
# --------------------------------
# LLM 包裝器 (OpenAI API Compatible)
# --------------------------------
class LLMWrapper:
    """LLM 包裝器 (使用 OpenAI API / llama-server)"""

    def __init__(self, base_url: str = "http://localhost:8080/v1", api_key: str = "lm-studio"):
        self.base_url = base_url
        self.api_key = api_key
        self.client: Optional[OpenAI] = None
        self.model_name = "ministral-3-14b" # Placeholder, server determines actual model

    def load_model(self) -> bool:
        """
        連接到 llama-server
        注意：這裡不再負責載入模型檔案，而是確保 Server 可連接。
        模型載入由 llama-server 啟動參數決定。
        """
        try:
            logger.info(f"正在連接 LLM Server: {self.base_url}")
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            
            # 測試連接 (List models)
            models = self.client.models.list()
            logger.info(f"✅ 連接成功。可用模型: {[m.id for m in models.data]}")
            return True

        except Exception as e:
            logger.error(f"無法連接 LLM Server: {e}")
            logger.error("請確保已啟動: ./llama-server -m ...")
            return False

    def generate(self, prompt: str, override_params: Optional[Dict] = None) -> str:
        """生成回應"""
        if self.client is None:
            raise RuntimeError("尚未連接 Server，請先呼叫 load_model()")

        params = {**DEFAULT_GEN_PARAMS, **(override_params or {})}
        
        # 移除不支援的參數
        if "stop" in params and isinstance(params["stop"], list):
            # OpenAI API 通常支援最多 4 個 stop sequences
            pass
        
        # 移除 llama-cpp 特有參數
        params.pop("grammar", None) 

        try:
            # 使用 Completion API (llama-server 支援 /v1/completions 用於原始補全)
            # 或者 Chat API。這裡 Prompt 是原始文字，建議用 completions。
            response = self.client.completions.create(
                model=self.model_name,
                prompt=prompt,
                max_tokens=params.get("max_tokens", 1000),
                temperature=params.get("temperature", 0.1),
                stop=params.get("stop", None),
                # top_p, frequency_penalty 等可依需添加
            )
            return response.choices[0].text
        except Exception as e:
            logger.error(f"生成失敗: {e}")
            raise

    def reset_cache(self):
        """
        Server 模式下通常不需要手動 reset context，
        因為每個 request 是獨立的 (Stateless unless using context caching slots explicitly).
        llama-server 會自動管理 slot。
        """
        pass

    def unload_model(self):
        """Server 模式下無法由 Client 卸載模型"""
        pass

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
SYSTEM_PROMPT_AUDITOR = load_prompt("Auditor") # Load the new Auditor prompt

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
    json_match = re.search(r'```json\s*(.*?)```', response, re.DOTALL)
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


# --------------------------------
# JSON Schema / Grammar (Disabled for OpenAI API)
# --------------------------------
# OpenAI API does not support GBNF grammars directly in the same way.
# We will rely on prompt engineering and json_repair.

def get_agent1_grammar():
    """Grammar disabled for server mode"""
    return None

def get_auditor_grammar():
    """Grammar disabled for server mode"""
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

Now evaluate the ABSORB capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "absorb", grammar=get_agent1_grammar())
    
    if not result:
        return None

    return DimensionScore(
        dimension="absorb",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

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

Now evaluate the ADOPT capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""
    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "adopt", grammar=get_agent1_grammar())
    if not result: return None

    return DimensionScore(
        dimension="adopt",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

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

Now evaluate the TRANSFORM capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""
    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "transform", grammar=get_agent1_grammar())
    if not result: return None

    return DimensionScore(
        dimension="transform",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

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

Now evaluate the ANTICIPATE capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""
    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "anticipate", grammar=get_agent1_grammar())
    if not result: return None

    return DimensionScore(
        dimension="anticipate",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

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

Now evaluate the REBOUND capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""
    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "rebound", grammar=get_agent1_grammar())
    if not result: return None

    return DimensionScore(
        dimension="rebound",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

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

Now evaluate the LEARN capability and output JSON.
IMPORTANT: Provide ONLY ONE sentence of evidence and ONLY ONE sentence of reasoning.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    result = run_agent1_with_retry(llm_wrapper, prompt, relevant_context, "learn", grammar=get_agent1_grammar())
    if not result: return None

    return DimensionScore(
        dimension="learn",
        score=float(result.get("score", 0)),
        evidence=result.get("evidence", []),
        reasoning=result.get("reasoning", "")
    )

# --------------------------------
# 主評分函數
# --------------------------------

def score_resilience(
    llm_wrapper: LLMWrapper,
    company: str,
    year: int,
    report_data: Dict[str, str],
    enable_reviewer: bool = True
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

    # 單 Agent 執行模式（優化版）：一次性載入模型，中間使用 reset_cache() 清空 Context
    # 優點：
    # 1. 減少 6 次模型載入/卸載 IO 時間（節省 ~10s）
    # 2. reset_cache() 瞬間清空 KV cache，確保 Agent 間 Context 隔離
    # 3. 保持單 Agent 內存優勢 (Context 不會累積)

    try:
        # 1. 載入模型（一次性）
        if not llm_wrapper.load_model():
            logger.error("❌ 模型載入失敗，終止評分")
            return score_obj

        agent_functions = [
            ("absorb", agent_absorb),
            ("adopt", agent_adopt),
            ("transform", agent_transform),
            ("anticipate", agent_anticipate),
            ("rebound", agent_rebound),
            ("learn", agent_learn),
        ]

        for agent_name, agent_func in agent_functions:
            logger.info(f"🔄 執行 {agent_name.upper()} Agent")

            # 2. 執行 Agent
            try:
                result = agent_func(llm_wrapper, company, year, report_data)
                setattr(score_obj, agent_name, result)
            except Exception as e:
                logger.error(f"❌ {agent_name} Agent 執行失敗: {e}")
                setattr(score_obj, agent_name, None)

            # 3. 清空 Cache (Critical for isolation)
            llm_wrapper.reset_cache()
            
            # 強制回收 Python GC (Selection: Optional safety)
            # import gc; gc.collect()

        # 計算整體分數
        score_obj.calculate_overall()

        # 4. 執行評分員審核 (Reviewer Agent)
        if enable_reviewer:
            logger.info("🔄 執行 Reviewer Agent（審核所有評分）")
            try:
                reviews = review_all_scores(llm_wrapper, score_obj)
                
                # 將審核結果填回 score_obj
                for dim_name, review_result in reviews.items():
                    dim_score = getattr(score_obj, dim_name)
                    if dim_score:
                        dim_score.review = review_result
            except Exception as e:
                logger.error(f"❌ Reviewer Agent 執行失敗: {e}")
        else:
            logger.info("ℹ️ 跳過 Reviewer Agent (使用者設定)")

    finally:
        # 5. 確保最後卸載模型
        llm_wrapper.unload_model()

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



def review_all_scores(
    llm_wrapper: LLMWrapper,
    score: ResilienceScore,
    # report_context: str # Unused in new prompt constraint
) -> Dict[str, ReviewResult]:
    """審核所有維度的評分 (Batch Mode)"""
    logger.info("\n=== 開始評分員審核 (Lead Auditor Batch) ===")
    
    # 1. 組建 Input JSON
    # Map lowercase dimension names to CAPS keys required by Lead Auditor
    # Keys: ABSORB, ADAPT, TRANSFORM, ANTICIPATE, REBOUND, LEARN
    # Note: 'adopt' in code corresponds to 'ADAPT' in standard/prompt? 
    # Let's check the prompt instructions: "ADAPT" is one of the keys.
    # Code uses 'adopt' for variable/capability name. I should safely map 'adopt' -> 'ADAPT'.
    
    mapping = {
        "absorb": "ABSORB",
        "adopt": "ADAPT",
        "transform": "TRANSFORM",
        "anticipate": "ANTICIPATE",
        "rebound": "REBOUND",
        "learn": "LEARN"
    }
    
    input_data = {}
    
    for dim_lower, dim_upper in mapping.items():
        dim_score = getattr(score, dim_lower)
        if dim_score:
            input_data[dim_upper] = {
                "evidence": dim_score.evidence,
                "reasoning": dim_score.reasoning,
                "score": int(dim_score.score)
            }
        else:
            # Handle missing scores gracefully? Or skip?
            # Auditor prompt implies it receives all 6.
            # Let's provide dummy entry if missing so Auditor can force it to 0
            input_data[dim_upper] = {
                "evidence": [],
                "reasoning": "Scoring failed or missing",
                "score": 0
            }

    input_json_str = json.dumps(input_data, indent=2, ensure_ascii=False)

    # 2. Construct Prompt
    prompt = f"""{SYSTEM_PROMPT_AUDITOR}

# INPUT DATA (Junior Agent Reports):

{input_json_str}

---

Now perform the Logic & Consistency Check for all 6 capabilities and output the single JSON object.
IMPORTANT: Provide ONLY ONE sentence for 'audit_note' and 'final_reasoning'.
<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>
"""

    # 3. Call LLM
    try:
        response = llm_wrapper.generate(
            prompt, 
            override_params={
                "temperature": 0.1, 
                "max_tokens": 2000, # Increased for larger output
                "grammar": get_auditor_grammar()
            }
        )
        
        # 4. Parse Result
        result_json = parse_json_response(response)
        if not result_json:
            logger.error("❌ Lead Auditor JSON parsing failed")
            return {}

        # 5. Convert to ReviewResult objects
        reviews = {}
        # Map back UPPER -> lower
        reverse_mapping = {v: k for k, v in mapping.items()}
        
        for key_upper, audit_data in result_json.items():
            key_lower = reverse_mapping.get(key_upper)
            if not key_lower:
                continue
                
            reviews[key_lower] = ReviewResult(
                dimension=key_lower,
                original_score=input_data[key_upper]["score"],
                status=audit_data.get("status", "UNKNOWN"),
                final_score=float(audit_data.get("final_score", 0)),
                final_reasoning=audit_data.get("final_reasoning", ""),
                audit_note=audit_data.get("audit_note", "")
            )
            
            logger.info(f"  {key_upper}: {audit_data.get('status')} -> {audit_data.get('final_score')} (Note: {audit_data.get('audit_note')})")

        return reviews

    except Exception as e:
        logger.error(f"Lead Auditor execution failed: {e}")
        return {}


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
            logger.info("\n=== 評分結果 ===")
            logger.info(f"公司: {score.company} ({score.year})")
            logger.info(f"整體分數: {score.overall_score:.1f}/100")
            # logger.info(f"整體信心: {score.overall_confidence:.2f} (平均值: 0=缺乏, 1=適度, 2=強烈)")

            logger.info("\n六維度分數:")
            for dim_name in ["absorb", "adopt", "transform", "anticipate", "rebound", "learn"]:
                dim_score = getattr(score, dim_name)
                if dim_score:
                    
                    review_msg = ""
                    if dim_score.review:
                        status_icon = "✅" if dim_score.review.status == "APPROVED" else "⚠️"
                        review_msg = f" | 審核: {status_icon}"
                        if dim_score.review.status == "CORRECTED":
                            review_msg += f" 建議: {dim_score.review.audit_note[:30]}..."

                    logger.info(f"  - {dim_name.capitalize()}: {dim_score.score}{review_msg}")
                else:
                    logger.info(f"  - {dim_name.capitalize()}: N/A (評分失敗)")

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
    report_data: Dict[str, str],
    enable_reviewer: bool = True
) -> Optional[ResilienceScore]:
    """
    向後相容函數 - 對應 v1.0 的 agent1_score_report
    實際調用 score_resilience
    """
    return score_resilience(llm_wrapper, company, year, report_data, enable_reviewer=enable_reviewer)

