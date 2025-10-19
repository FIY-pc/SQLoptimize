import logging
import sys
import os
import threading
import json
from datetime import datetime
from src.config import get_settings

def set_log_level():
    settings = get_settings()
    
    # 获取进程ID和线程ID
    process_id = os.getpid()
    thread_id = threading.get_ident()
    
    # 尝试获取worker信息，如果没有则使用进程ID作为worker标识
    worker_id = os.environ.get('UVICORN_WORKER_ID', f'worker-{process_id}')
    
    # 创建简洁的日志格式化器 - 类似现代日志库的格式
    formatter = logging.Formatter(
        fmt=f'%(asctime)s.%(msecs)03d | %(levelname)-5s | [{worker_id}] %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(parse_log_level(settings.log_level))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 可选的颜色支持
    try:
        import colorlog
        color_formatter = colorlog.ColoredFormatter(
            f'%(log_color)s%(asctime)s.%(msecs)03d | %(levelname)-5s | [%(reset)s{worker_id}%(log_color)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(color_formatter)
    except ImportError:
        # 如果没有安装 colorlog，使用普通格式
        pass
    
    # 配置uvicorn相关的日志记录器
    configure_uvicorn_logging(settings.log_level, process_id, thread_id, worker_id)

def configure_uvicorn_logging(log_level: str, process_id: int, thread_id: int, worker_id: str):
    """配置uvicorn相关的日志记录器"""
    uvicorn_loggers = [
        'uvicorn',
        'uvicorn.error',
        'uvicorn.access',
        'uvicorn.asgi',
        'fastapi',
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        'sqlalchemy.dialects',
    ]
    
    # 创建uvicorn专用的格式化器
    uvicorn_formatter = logging.Formatter(
        fmt=f'%(asctime)s.%(msecs)03d | %(levelname)-5s | [{worker_id}] %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(parse_log_level(log_level))
        
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(uvicorn_formatter)
        logger.addHandler(console_handler)
        
        # 防止日志传播到根记录器（避免重复）
        logger.propagate = False

def setup_worker_logging():
    """为多worker环境设置日志配置"""
    settings = get_settings()
    
    # 获取当前worker信息
    process_id = os.getpid()
    thread_id = threading.get_ident()
    worker_id = os.environ.get('UVICORN_WORKER_ID', f'worker-{process_id}')
    
    # 设置环境变量以便其他模块使用
    os.environ['CURRENT_WORKER_ID'] = worker_id
    
    # 配置日志
    set_log_level()
    
    # 记录worker启动信息
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker_id} started")

class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器，适合结构化日志"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        super().__init__()
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "worker": self.worker_id,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_json_logging():
    """设置JSON格式的日志"""
    settings = get_settings()
    process_id = os.getpid()
    worker_id = os.environ.get('UVICORN_WORKER_ID', f'worker-{process_id}')
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(parse_log_level(settings.log_level))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建JSON格式化器
    json_formatter = JSONFormatter(worker_id)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # 配置uvicorn相关的日志记录器
    configure_uvicorn_logging(settings.log_level, process_id, threading.get_ident(), worker_id)

def parse_log_level(log_level: str) -> int:
    if log_level == "DEBUG":
        return logging.DEBUG
    elif log_level == "INFO":
        return logging.INFO
    elif log_level == "WARNING":
        return logging.WARNING
    elif log_level == "ERROR":
        return logging.ERROR
    elif log_level == "CRITICAL":
        return logging.CRITICAL
    else:
        return logging.INFO