import logging
import sys
from src.config.environment import Environment

def setup_logging():
    log_level_str = Environment.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set third-party logger levels if needed to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
