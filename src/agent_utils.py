import json
import logging
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)

class TruncationError(Exception):
    """Raised when JSON parsing succeeds but required keys are missing (likely truncated)."""
    pass

def parse_json_response(response: str) -> Optional[Dict]:
    """
    解析 JSON 回應 (複製自 quantify.py，避免循環依賴或重複代碼)
    """
    import json_repair

    # 1. 直接解析
    try:
        return json.loads(response)
    except:
        pass

    # 2. 提取 JSON code block
    json_match = re.search(r'```json\s*(\\{.*?\\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass

    # 3. 提取 {...}
    json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
            
    # 4. 使用 json_repair 強力修復 (處理截斷或格式錯誤)
    try:
        # returns parsed object directly if successful
        decoded_object = json_repair.repair_json(response, return_objects=True)
        if isinstance(decoded_object, (dict, list)):
             logger.info("⚠️ JSON parsed with json_repair (likely truncated)")
             return decoded_object
    except Exception as e:
        logger.warning(f"json_repair failed: {e}")

    logger.error(f"無法解析 JSON. Content: {response[:500]}...")
    return None

def validate_agent1_output(raw_output: str, section_text: str) -> Optional[Dict]:
    """
    驗證 Agent1 回傳的 JSON 是否符合格式與基本邏輯。
    通過時回傳 parsed dict；失敗時回傳 None。
    """
    data = parse_json_response(raw_output)
    if data is None:
        logger.warning("Validation Failed: JSON Parse Error")
        return None

    # 必要欄位檢查
    required_keys = {"evidence", "reasoning", "score"}
    if not required_keys.issubset(data.keys()):
        missing = required_keys - data.keys()
        logger.warning(f"Validation Failed: Missing keys. Found {data.keys()}")
        # 若缺少 keys，很可能是被截斷 (尤其是缺少 score/reasoning)
        # 拋出特殊異常以觸發 Adaptive Retry
        raise TruncationError(f"Missing keys: {missing}")
        # return None # 舊邏輯

    # score 檢查
    score = data.get("score")
    # 允許 float (e.g., 3.5) 或 int，但要在 0-4 範圍內
    if not isinstance(score, (int, float)) or not (0 <= score <= 4):
        logger.warning(f"Validation Failed: Invalid score {score}")
        return None

    # evidence 檢查：必須是 list[str]
    evidence = data.get("evidence")
    if not isinstance(evidence, list):
        logger.warning("Validation Failed: Evidence is not a list")
        return None
    for item in evidence:
        if not isinstance(item, str):
            logger.warning("Validation Failed: Evidence item is not a string")
            return None

    # （選配）字串是否在原文中出現（防止幻覺與亂 key 入）
    # 放寬：允許部分不匹配（例如 LLM 稍微修改了標點或空格），或者只檢查前 N 個字
    # 這裡採用嚴格檢查但允許 strip()
    # 另一個策略：計算 'miss' 的比例，如果超過 50% 的 evidence 找不到才報錯
    
    import rapidfuzz 

    miss_count = 0
    for quote in evidence:
        clean_quote = quote.strip()
        if not clean_quote:
            continue
            
        # 1. Exact match (Fastest)
        if clean_quote in section_text:
            continue
            
        # 2. Relaxed match (Fast)
        if clean_quote.replace('\n', ' ') in section_text.replace('\n', ' '):
            continue

        # 3. Fuzzy match (Robust but slower)
        # partial_ratio handles substrings well ("quote is a part of text")
        # score > 85 usually means very high similarity with minor changes
        match_score = rapidfuzz.fuzz.partial_ratio(clean_quote.lower(), section_text.lower())
        
        if match_score >= 50:
            # logger.info(f"Fuzzy match found: {match_score:.1f}%") # Optional debug
            continue
            
        miss_count += 1
        logger.warning(f"❌ Evidence Mismatch (Score: {match_score:.1f}%):\n   Quote: '{clean_quote}'")

    if len(evidence) > 0 and miss_count > len(evidence) * 0.5: # 容忍 50% 錯誤 mismatch (可能是格式問題)
         logger.warning(f"Validation Failed: Too many evidence mismatches ({miss_count}/{len(evidence)})")
         # Debug logs
         print(f"\n[DEBUG] Validation Failed for Evidence ({miss_count}/{len(evidence)} failed)")
         for i, quote in enumerate(evidence):
             print(f"  {i+1}. {quote[:100]}... [FAIL/FUZZY SCORE CHECK NEEDED]")

         return None

    # reasoning 檢查
    if not isinstance(data.get("reasoning"), str):
        logger.warning("Validation Failed: Reasoning is not a string")
        return None
    
    return data

def run_agent1_with_retry(
    llm_wrapper: Any, 
    prompt: str, 
    section_text: str, 
    capability_name: str,
    max_retries: int = 2,
    grammar: Any = None
) -> Optional[Dict]:
    """
    對指定能力（如 ABSORB）呼叫 Agent1，驗證 JSON，
    若失敗則重跑，最多 max_retries 次。
    成功時回傳 parsed dict，失敗時回傳 None (或丟出例外，這裡選擇回傳 None 由呼叫者處理)。
    """
    last_error = None
    
    # 第一次嘗試 + max_retries
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"🔄 Retry Agent 1 for {capability_name} (Attempt {attempt}/{max_retries})")
        
        try:
            # Generate
            override_params = {
                "temperature": 0.1, # 保持低溫
                "max_tokens": 4096,
                "stop": ["}```", "\n\n\n"],
            }
            if grammar:
                override_params["grammar"] = grammar

            raw_output = llm_wrapper.generate(
                prompt,
                override_params=override_params
            )
            
            # Save raw output for debugging if needed
            # logger.debug(f"Raw output ({capability_name}): {raw_output[:200]}...")

            # Validate
            try:
                result = validate_agent1_output(raw_output, section_text)
                if result is not None:
                    return result
            except TruncationError as te:
                logger.warning(f"⚠️ Truncation detected: {te}")
                # Adaptive Retry Logic
                # Next attempt will use a stricter prompt
                if attempt < max_retries:
                    # Tiered limits
                    if attempt == 0:
                         limit_n = 2
                    else:
                         limit_n = 1
                    
                    truncation_instruction = (
                        f"\n\nIMPORTANT: Your previous output was truncated. "
                        f"Please list AT MOST {limit_n} piece(s) of evidence to ensure the JSON is valid."
                    )
                    
                    if truncation_instruction not in prompt:
                         prompt += truncation_instruction
                         logger.info(f"🔧 Adaptive Retry: Added truncation instruction (Limit {limit_n})")
                
                # Treat as normal failure for now (the loop will retry with new prompt)
                last_error = f"TruncationError: {te}"
                continue 

            last_error = raw_output
            logger.warning(f"❌ Validation failed for {capability_name}")
            logger.warning(f"Invalid Output: {raw_output[:500]}...") # Log part of the output
            
        except Exception as e:
            logger.error(f"Generate failed for {capability_name}: {e}")
            last_error = str(e)

    logger.error(
        f"Agent1 failed to produce valid JSON for {capability_name} "
        f"after {max_retries + 1} attempts."
    )
    return None
