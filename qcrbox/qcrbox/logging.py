import sys
from loguru import logger

logger.level("ERROR", color="<red><bold>")
logger.level("WARNING", color="<yellow><bold>")
logger.level("SUCCESS", color="<green><bold>")
logger.level("INFO", color="<blue><bold>")
logger.level("DEBUG", color="<light-black>")

logger.remove()  # Remove all handlers (including the default one) to start from a clean slate.
logger.add(sys.stderr, level="DEBUG", colorize=True, format="<green>{time:YYYY-mm-dd HH:MM:SS}</green> | {level} | <level>{message}</level>")
