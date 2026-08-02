from enum import Enum


class State(str, Enum):

    NONE = "NONE"

    PHONE = "PHONE"

    CODE = "CODE"

    PASSWORD = "PASSWORD"

    SOURCE_CHANNEL = "SOURCE_CHANNEL"

    TARGET_CHANNEL = "TARGET_CHANNEL"

    REMOVE_LAST_LINES = "REMOVE_LAST_LINES"
