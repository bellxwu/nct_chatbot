'''
Description: Centralized logging configuration for the NCT project.

Import get_logger() from here in every module. Logging is configured once
per process, and all modules share a single timestamped log file per run.
'''
# %%
import logging
import logging.config
import os
from datetime import datetime
import config

# %%
LOG_DIR = config.log_dir
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ensure the log directory exists before any FileHandler opens a file.
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Computed ONCE, at import -> one file per process/run, shared by all modules.
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"nct_{RUN_ID}.log"

# %%
# "file" and "console" are handler/formatter labels and can be renamed.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "file": {"format": "%(asctime)s, %(name)s, %(filename)s, %(lineno)d, %(funcName)s, %(levelname)s, %(message)s"},
        "console": {"format": "%(asctime)s, %(filename)s, %(lineno)d, %(levelname)s, %(message)s"},
    },
    "handlers": {
        "file": {"class": "logging.FileHandler", "filename": LOG_FILE, "formatter": "file"},
        "console": {"class": "logging.StreamHandler", "formatter": "console"},
    },
    "root": {"level": LOG_LEVEL, "handlers": ["file", "console"]},
}

# %%

def setup_logging():
    """Apply the logging config once. Idempotent via the root logger's state."""
    if not logging.getLogger().hasHandlers():
        logging.config.dictConfig(LOGGING)


# %%
def get_logger(name):
    """Return a logger, ensuring logging is configured on first use."""
    setup_logging()
    return logging.getLogger(name)
