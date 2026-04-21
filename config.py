import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PSD_TEMPLATE_PATH = os.getenv("PSD_TEMPLATE_PATH", "psd_templates/template.psd")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output/")
USER_IMAGE_DIR = os.getenv("USER_IMAGE_DIR", "user_images/")

def validate_config():
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is missing")
    elif ":" not in TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN format is invalid")
    if not os.path.exists(PSD_TEMPLATE_PATH):
        errors.append(f"PSD not found at: {PSD_TEMPLATE_PATH}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(USER_IMAGE_DIR, exist_ok=True)
    if errors:
        for error in errors: logger.error(f"Config Error: {error}")
        return False
    return True

if not validate_config():
    logger.warning("Check your .env file settings.")