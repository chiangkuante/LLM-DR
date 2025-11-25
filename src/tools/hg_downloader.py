import os
from huggingface_hub import snapshot_download

# 1. 指定你的模型 ID (以 Llama 3 GGUF 為例)
repo_id = "unsloth/gpt-oss-20b-GGUF"

# 2. 指定你本地的目標資料夾
# (建議使用絕對路徑，並確保資料夾存在)
# (這裡使用相對路徑 './my_model_directory' 作為範例)
target_path = os.path.join(os.getcwd(), "models")

# Ensure the directory exists
os.makedirs(target_path, exist_ok=True)

print(f"準備將模型下載至: {target_path}")

# 3. 執行下載
# 我們也加入了 allow_patterns 只下載 Q4_K_M 版本，避免下載所有檔案
model_directory = snapshot_download(
    repo_id=repo_id,
    local_dir=target_path,  # <-- 關鍵參數
    allow_patterns="gpt-oss-20b-Q4_0.gguf", # 範例：只抓 Q4_K_M GGUF 檔
    local_dir_use_symlinks=False # 建議設為 False，直接複製檔案
)

print(f"模型檔案已成功下載至: {model_directory}")
# (注意：這裡返回的 model_directory 就是你傳入的 target_path)