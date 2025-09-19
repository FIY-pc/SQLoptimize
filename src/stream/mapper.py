from src.schemas.stream_chunk import NodeChunk, Chunk
from src.utils import get_unix_timestamp
import json
import logging
logger = logging.getLogger(__name__)

def map_langgraph_node_chunk(chunk) -> Chunk:
    """
    将 LangGraph "values"模型流式输出结构: {"节点名": State} 转换为 Chunk 对象
    """
    # 处理不同类型的输入
    if isinstance(chunk, str):
        try:
            chunk = json.loads(chunk)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON string: {chunk}, error: {e}")
    elif not isinstance(chunk, dict):
        raise ValueError(f"Invalid chunk type: {type(chunk)}, expected dict or str")
    
    # 确保 chunk 是字典且不为空
    if not chunk:
        raise ValueError(f"Empty chunk: {chunk}")
    
    # 获取第一个键值对
    items = list(chunk.items())
    if not items:
        raise ValueError(f"Empty chunk: {chunk}")
    
    node_name, node_data = items[0]
    logger.info(f"Processing node: {node_name}")
    
    # 处理 node_data
    if isinstance(node_data, dict):
        # 创建 node_data 的副本并添加 node_name
        node_data_copy = node_data.copy()
        node_data_copy['node_name'] = node_name
        
        try:
            filtered_response = NodeChunk(**node_data_copy)
            data = Chunk(
                type="node_chunk", 
                data=filtered_response, 
                timestamp=get_unix_timestamp()
            )
            return data
        except Exception as e:
            logger.error(f"Failed to create NodeChunk from data: {node_data_copy}, error: {e}")
            raise ValueError(f"Failed to create NodeChunk: {e}")
    else:
        raise ValueError(f"Node data must be dict, got: {type(node_data)}, value: {node_data}")
