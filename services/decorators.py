import logging
import time
from functools import wraps

from fastapi import HTTPException


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request/Response logging decorator
def log_requests(func):
    """Log request and response details"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(f"[{request_id}] Starting {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"[{request_id}] Completed {func.__name__} in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{request_id}] Failed {func.__name__} in {duration:.2f}s: {str(e)}")
            
            raise HTTPException(status_code=400, detail= str(e))
    return wrapper
