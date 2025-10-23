import logging
import sys
import os
import json
from datetime import datetime
from src.config import get_settings

def setup_logging():
    """统一设置日志配置"""
    settings = get_settings()
    worker_id = os.environ.get('UVICORN_WORKER_ID', f'worker-{os.getpid()}')
    
    # 创建格式化器
    formatter = create_formatter(worker_id)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # 清除现有处理器并添加新的
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 配置第三方库日志级别
    configure_third_party_logging(settings.log_level)

def create_formatter(worker_id: str):
    """创建日志格式化器"""
    fmt = f'%(asctime)s.%(msecs)03d | %(levelname)-5s | [{worker_id}] %(name)s: %(message)s'
    
    try:
        import colorlog
        return colorlog.ColoredFormatter(
            f'%(log_color)s{fmt}',
            datefmt='%Y-%m-%dT%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green', 
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    except ImportError:
        return logging.Formatter(fmt=fmt, datefmt='%Y-%m-%dT%H:%M:%S')

def configure_third_party_logging(log_level: str):
    """配置第三方库日志级别"""
    # 第三方库日志级别映射表
    logger_configs = {
        # SQLAlchemy
        'sqlalchemy.engine': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        'sqlalchemy.pool': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        'sqlalchemy.dialects': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        'sqlalchemy.orm': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        'sqlalchemy.engine.Engine': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        'sqlalchemy.pool.Pool': 'DEBUG' if log_level == 'DEBUG' else 'WARNING',
        
        # 其他第三方库
        'urllib3.connectionpool': 'WARNING',
        'urllib3.util.retry': 'WARNING',
        'requests.packages.urllib3': 'WARNING',
        'requests': 'WARNING',
        'httpx': 'INFO' if log_level == 'DEBUG' else 'WARNING',
        'httpcore': 'WARNING',
        'asyncio': 'WARNING',
        'openai': 'WARNING',
        'tiktoken': 'WARNING',
    }
    
    for logger_name, level in logger_configs.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level))
        logger.propagate = False