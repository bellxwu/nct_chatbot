'''
Description: Configuration file for the NCT query project. 
'''
# %%
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
# %%
# --- Base Directory ---
base_dir = Path(__file__).resolve().parents[1]

# --- Log Directory ---
log_dir = base_dir / os.getenv("LOG_DIR")
# %%
