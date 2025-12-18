from __future__ import annotations

import os
from dotenv import load_dotenv

# ============================================================
# 環境設定
# ============================================================

load_dotenv()

# 可用性旗標（預設關閉，匯入成功再開）
CHATGROQ_AVAILABLE = False
DDGS_AVAILABLE = False

try:
    from langchain_groq import ChatGroq
    CHATGROQ_AVAILABLE = True
    print("✓ ChatGroq 可用")
except Exception:
    print("✗ ChatGroq 不可用")

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
    print("✓ DuckDuckGo Search 可用")
except Exception:
    print("✗ DuckDuckGo Search 不可用")


# ============================================================
# 模型測試
# ============================================================

# 要測試的模型列表（來自 AgentBook_DualLayer.py 的實際配置）
MODELS_TO_TEST = [
    "groq/openai/gpt-oss-120b",
    "groq/openai/gpt-oss-20b",
    "groq/llama-3.3-70b-versatile",
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "groq/qwen/qwen3-32b",
    "groq/moonshotai/kimi-k2-instruct-0905",
]


def test_model(model_name: str) -> bool:
    """測試單一模型是否可用"""
    if not CHATGROQ_AVAILABLE:
        print(f"  ✗ {model_name}: ChatGroq 未安裝")
        return False
    
    try:
        # 移除 groq/ 前綴
        name = model_name.replace("groq/", "")
        
        llm = ChatGroq(
            model=name,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.5,
            timeout=30,
            max_retries=1,
            max_tokens=50,
        )
        
        # 簡單測試
        response = llm.invoke("說一句話")
        result = response.content[:50].replace("\n", " ")
        print(f"  ✓ {model_name}: {result}...")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "404" in error_msg:
            print(f"  ✗ {model_name}: 模型不存在")
        else:
            print(f"  ✗ {model_name}: {error_msg[:50]}")
        return False


def test_all_models():
    """測試所有模型"""
    print("\n" + "=" * 60)
    print("🧪 模型可用性測試")
    print("=" * 60 + "\n")
    
    results = {}
    for model in MODELS_TO_TEST:
        results[model] = test_model(model)
    
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)
    
    available = [m for m, ok in results.items() if ok]
    unavailable = [m for m, ok in results.items() if not ok]
    
    print(f"\n✓ 可用模型 ({len(available)}):")
    for m in available:
        print(f"   • {m}")
    
    if unavailable:
        print(f"\n✗ 不可用模型 ({len(unavailable)}):")
        for m in unavailable:
            print(f"   • {m}")
    
    print("\n" + "=" * 60)
    return results


if __name__ == "__main__":
    test_all_models()