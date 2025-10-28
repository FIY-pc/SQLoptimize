from langgraph.config import get_stream_writer
from langchain_core.messages import AIMessageChunk

async def write_newline_to_stream(line_number: int = 1):
    """
    向流中写入换行符

    Args:
        line_number: 换行符的个数
    """
    writer = get_stream_writer()
    chunk = (AIMessageChunk(content=f"\n{line_number}"), {"langgraph_node": "generate_plans"})
    writer(chunk)