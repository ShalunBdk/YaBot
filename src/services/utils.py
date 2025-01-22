from datetime import datetime
import logging
import random
import re
import string
from typing import List
import pytz
import requests

from config import settings

class Utilities:
    """Class for handling various utility operations."""

    def __init__(self):
        self.words = [
            "air",
            "clean",
            "work",
            "desk",
            "file",
            "note",
            "call",
            "plan",
            "leaf",
            "task",
            "print",
            "plant",
            "light",
            "shade",
            "water",
            "dust",
            "chair",
            "glass",
            "space",
            "green",
            "flow",
            "cloud",
            "ozone",
            "smart",
            "laser",
            "breeze",
            "sun",
            "star",
            "calm",
            "plant",
            "room",
            "floor",
            "quiet",
            "break",
            "team",
            "focus",
            "goal",
            "shift",
            "drive",
            "write",
            "clear",
            "draft",
            "point",
            "idea",
            "pencil",
            "table",
            "email",
            "power",
            "press",
            "order",
            "graph",
            "speed",
            "chart",
            "data",
            "wifi",
            "enter",
            "exit",
            "input",
            "logic",
            "mind",
            "train",
            "group",
            "range",
            "quick",
            "pulse",
            "reset",
            "align",
            "brief",
            "short",
            "file",
            "note",
            "panel",
            "share",
            "code",
            "log",
            "type",
            "solar",
            "smile",
            "grape",
            "field",
            "shine",
            "clear",
            "zone",
            "form",
            "report",
            "shift",
            "phase",
            "count",
            "glass",
            "draft",
            "mark",
            "sound",
            "white",
            "stone",
            "click",
            "light",
            "range",
            "robot",
            "mild",
            "relax",
            "palm",
            "wind",
            "cloud",
            "plant",
            "force",
            "line",
            "block",
            "space",
            "entry",
            "cycle",
            "mode",
            "smooth",
            "leaf",
            "count",
            "share",
            "brief",
            "panel",
            "drill",
            "bloom",
            "focus",
            "track",
            "scope",
            "view",
            "speed",
            "quick",
            "word",
            "phase",
            "align",
            "light",
            "chart",
            "laser",
            "limit",
            "smile",
            "plane",
            "pulse",
            "train",
            "scale",
            "build",
            "graph",
            "clean",
            "place",
            "click",
            "form",
            "frame",
            "press",
            "chill",
            "boost",
            "clear",
            "drive",
            "mark",
            "mood",
            "draft",
            "reset",
            "share",
            "block",
            "logic",
            "sound",
            "brief",
            "input",
            "count",
            "focus",
            "range",
            "start",
            "point",
            "score",
            "shine",
            "stone",
            "clear",
            "plant",
            "track",
            "field",
            "blend",
            "order",
            "frame",
            "file",
            "view",
            "share",
            "group",
            "score",
            "chart",
            "graph",
            "short",
            "limit",
            "phase",
            "solar",
        ]

    def generate_random_string(self, word_count: int = 3) -> str:
        """Generate a random password string."""
        words_selected = [random.choice(self.words).capitalize() for _ in range(word_count)]
        number = random.randint(0, 99)
        special_char = random.choice(["!", "@", "#", "$", "%", "&", "*"])
        return "".join(words_selected) + str(number) + special_char

    def get_sms_code(self, phone: str) -> str:
        """Generate and send SMS code."""
        message = "".join(random.choice(string.digits) for _ in range(6))
        data = {"number": phone, "message": message}
        
        try:
            result = requests.post(f"{settings.SMS_API_URL}/send_sms", json=data)
            logging.info(result.json())
            return message
        except requests.ConnectTimeout:
            logging.error("SMS шлюз не отвечает")
        except Exception as e:
            logging.error(f"Ошибка при отправке смс: {e}")
            raise

    def normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number format."""
        digits = re.sub(r"\D", "", phone_number)
        
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        elif not digits.startswith("7") and len(digits) == 10:
            digits = "7" + digits
            
        normalized_number = f"+{digits}"
        
        if len(normalized_number) == 12:
            return normalized_number
        raise ValueError(f"Неверный формат номера: {phone_number}")

    def format_utc_to_moscow(self, dt: datetime) -> str:
        """Format UTC datetime to Moscow timezone."""
        try:
            utc_dt = dt.astimezone(pytz.utc)
            moscow_dt = utc_dt.astimezone(pytz.timezone('Europe/Moscow'))
            return moscow_dt.strftime('%d.%m.%Y %H:%M')
        except AttributeError:
            return "Not found"
    