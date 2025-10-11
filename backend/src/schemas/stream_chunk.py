from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional, Dict, Any
from langchain_core.messages import AIMessageChunk

class Chunk(AIMessageChunk):
    metadata: Dict[str, Any] = Field(..., description="元数据")