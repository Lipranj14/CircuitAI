import logging
import time
from functools import wraps
from typing import Callable, Any

def setup_logger(name: str = "circuit_platform") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger()

def timed_execution(stage_name: str) -> Callable:
    """Decorator to measure and log execution time of pipeline stages."""
    def decorator(func: Callable) -> Callable:
        import asyncio
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            logger.info(f"[{stage_name}] Started")
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"[{stage_name}] Completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[{stage_name}] Failed after {duration:.3f}s: {str(e)}")
                raise
                
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            logger.info(f"[{stage_name}] Started")
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"[{stage_name}] Completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[{stage_name}] Failed after {duration:.3f}s: {str(e)}")
                raise
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
