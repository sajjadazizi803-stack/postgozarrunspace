import os

from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")

API_ID = int(os.getenv("API_ID"))

API_HASH = os.getenv("API_HASH")

SESSION_FOLDER = "sessions"

SUPPORT = "support"

ADMIN_ID = int(os.getenv("ADMIN_ID"))

from enum import Enum, auto


class AdState(Enum):

    ADD_GROUP = auto()

    SET_TEXT = auto()

    SET_FORWARD = auto()

    SET_INTERVAL = auto()
