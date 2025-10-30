from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional, Dict, Any
from langchain_core.messages import AIMessageChunk

class Chunk(AIMessageChunk):
    event: str = Field(default="", description="事件")
    reasoning_content: str = Field(default="", description="思维链内容")
    metadata: Dict[str, Any] = Field(..., description="元数据")

    def auto_set_reasoning_content(self):
        reasoning_content = self.additional_kwargs.get("reasoning_content", "")
        self.reasoning_content = reasoning_content