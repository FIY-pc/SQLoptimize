"""
API Key 工具函数
用于混淆API key以在响应中安全显示
"""

def mask_api_key(api_key: str) -> str:
    """
    混淆API key，保留前3位和后3位，中间用星号替换
    
    Args:
        api_key: 原始API key
        
    Returns:
        混淆后的API key字符串
    """
    if not api_key or len(api_key) <= 6:
        # 如果API key太短，全部用星号替换
        return "*" * len(api_key) if api_key else ""
    
    # 保留前3位和后3位，中间用星号替换
    prefix = api_key[:3]
    suffix = api_key[-3:]
    middle_length = len(api_key) - 6
    
    # 确保中间部分至少占一半长度
    min_middle_length = max(middle_length, len(api_key) // 2)
    masked_middle = "*" * min_middle_length
    
    return f"{prefix}{masked_middle}{suffix}"
