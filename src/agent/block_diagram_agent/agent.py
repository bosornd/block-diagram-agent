"""Block Diagram Agent — Converts user descriptions to Mermaid diagrams (Google ADK + Pydantic).
LLM: 환경변수 LLM_BASE_URL(또는 KSERVE_URL)이 있으면 해당 OpenAI 호환 엔드포인트(KServe 등) 사용, 없으면 Gemini 사용.
"""
import os

from google.adk.agents import Agent

from .schema import DiagramResponse


def get_llm_info():
    """현재 사용 중인 LLM 정보. 로컬 모델 여부 확인용."""
    base_url = (
        os.getenv("LLM_BASE_URL", "").strip()
        or os.getenv("KSERVE_URL", "").strip()
    )
    if base_url:
        if not base_url.rstrip("/").endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        model_name = os.getenv("LLM_MODEL_NAME", "local").strip() or "local"
        return {
            "provider": "local",
            "base_url": base_url,
            "model_name": model_name,
        }
    return {"provider": "gemini", "model": "gemini-2.0-flash"}


def _resolve_model():
    """LLM_BASE_URL 또는 KSERVE_URL이 설정되면 로컬(OpenAI 호환) 모델, 아니면 Gemini."""
    info = get_llm_info()
    if info["provider"] == "local":
        from google.adk.models.lite_llm import LiteLlm

        # 로컬(Ollama 등)은 키 검증 없음. LiteLLM이 api_key 필수로 요구하므로 더미 값 전달.
        return LiteLlm(
            model=f"openai/{info['model_name']}",
            api_base=info["base_url"],
            api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        )
    return "gemini-2.0-flash"


DIAGRAM_INSTRUCTION = """You are a diagram assistant. Your role is to generate block diagrams from the user's description.

Output: You must respond with a single JSON object that conforms to the provided schema (title, message, mermaid).

**Required:** title, message, and mermaid must all be written in the same language as the user's input. If the user writes in Korean, respond in Korean; if in English, respond in English.
"""

root_agent = Agent(
    name="diagram_agent",
    model=_resolve_model(),
    description="Generates block or flowchart diagrams from natural language descriptions using Mermaid.",
    instruction=DIAGRAM_INSTRUCTION,
    output_schema=DiagramResponse,
    output_key="diagram",
)
