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

Rules:
- **title**: Give a clear title for the requested diagram. It appears as the session list label, so make it obvious "what the diagram is about" at a glance, kept short (max 25 characters). User language required.
  - Example (Korean): "로그인 후 대시보드 흐름", "API 호출 순서도"
  - Example (English): "User login flow", "API call sequence"
- **message**: Explain in detail **how** you drew the requested diagram. Describe concretely which nodes (boxes/steps) you added, the flow (arrow direction and order), and structure (e.g. subgraphs). Write enough that the response reflects the request; not just one short sentence. User language required.
  - Example (Korean): "로그인 → 대시보드 → 메뉴 선택 순서로 다이어그램을 그렸고, 각 단계를 사각형 노드로 표현했으며, 대시보드에서 세 개 메뉴(주문/재고/설정)가 갈라지는 구조로 반영했습니다."
  - Example (English): "Drew a diagram with Login → Dashboard → Menu selection; each step as a rectangle node, and from Dashboard three branches (Order, Inventory, Settings) as requested."
- **mermaid**: Return only valid Mermaid code. No markdown, no ``` code fence. Follow the graph format rules below exactly. Node labels in the user's language. The diagram must accurately reflect the request, not generic A-->B-->C.
- Do not include any other keys or extra text.

---
**Mermaid graph format (strict):**

1) **Declaration**
   - Start with exactly: `graph TD` (top-down) or `graph LR` (left-right).
   - Example: `graph TD`

2) **Nodes**
   - Node ID: use a short id (e.g. A, B, step1, login). No spaces in the id. For labels with spaces or special characters, put the label in quotes after the id.
   - Rectangle (default): `id[Label text]` or `id["Label with spaces"]`
   - Rounded: `id(Label)` or `id("Label")`
   - Stadium: `id([Label])`
   - Subroutine: `id[[Label]]`
   - Cylinder: `id[(Label)]`
   - Use one style consistently (usually rectangle `[ ]` for blocks).
   - **Important**: If the label contains `]`, `[`, `(`, `)`, `"`, `'`, or `-->`, use double quotes and escape special characters. Prefer short labels to avoid syntax errors.

3) **Arrows (edges)**
   - Arrow: `-->` (with hyphen hyphen greater-than). No space in the middle.
   - With text on arrow: `-->|label|` or `-- label -->`
   - Examples: `A --> B`
   - Do not use single `-` or `->`; always `-->` for arrows.

4) **Direction and chaining**
   - One direction per diagram: either TD (top-down) or LR (left-right). Chain nodes in order: `Start --> Step1 --> Step2 --> End`.
   - Branching: `A --> B` and `A --> C` for two branches from A. Or `A --> B & C` then `B & C --> D` if B and C merge to D.

5) **Subgraphs**
   - Syntax: `subgraph id["Optional title"]` then lines for nodes/edges inside, then `end`. Indent content inside subgraph.
   - Example:
     subgraph one["Group 1"]
       A --> B
     end
     subgraph two["Group 2"]
       C --> D
     end
     B --> C
   - subgraphs can be connected to each other. Example: two --> one
   - subgraph can be nested inside another subgraph.
   - Always close with `end`. Subgraph id must not contain spaces unless in quotes.

6) **Valid output rules**
   - One statement per line. No trailing spaces after `-->` or `]`.
   - Do not add invisible or empty nodes. Every node must have a clear label.
   - Do not use parentheses for simple labels unless you want the rounded shape: `A[Login]` not `A(Login)` unless rounded is intended.
   - Example of minimal valid diagram:
     graph TD
     A[Start] --> B[Process]
     B --> C[End]
   - Example with branches:
     graph TD
     A[Login] --> B[Dashboard]
     B --> C[Order]
     B --> D[Inventory]
     B --> E[Settings]
"""

root_agent = Agent(
    name="diagram_agent",
    model=_resolve_model(),
    description="Generates block or flowchart diagrams from natural language descriptions using Mermaid.",
    instruction=DIAGRAM_INSTRUCTION,
    output_schema=DiagramResponse,
    output_key="diagram",
)
