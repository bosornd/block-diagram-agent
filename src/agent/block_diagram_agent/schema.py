"""Pydantic schema for agent structured output (title / message / mermaid)."""
from pydantic import BaseModel, Field


class DiagramResponse(BaseModel):
    """Structured diagram agent response. Consumed by session/UI via output_key.
    Required: title, message, and mermaid must all be in the same language as the user's input.
    """

    title: str = Field(
        description="Clear title for the requested diagram. Session list label, max 25 chars. Must match user language. e.g. 'Login then dashboard flow', 'User login flow'"
    )
    message: str = Field(
        description="Detailed explanation of how the requested diagram was drawn. Describe nodes, flow, and structure concretely. Must match user language. e.g. 'Drew a flowchart TD in order Login → Dashboard → Menu selection, with each step as a rectangle node.'"
    )
    mermaid: str = Field(
        description="Mermaid diagram code. flowchart LR/TD or subgraph etc. Plain code only, no markdown/code fence. Node labels in user language per request."
    )
