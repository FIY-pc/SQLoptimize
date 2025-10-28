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
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

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

