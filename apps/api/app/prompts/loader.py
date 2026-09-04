import os
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "v1"


@lru_cache()
def load_system_prompt(version: str = "v1") -> str:
    """Loads and compiles base, safety, and multilingual instructions from markdown prompt files."""
    base_path = PROMPTS_DIR / "base.md"
    safety_path = PROMPTS_DIR / "safety.md"
    lang_path = PROMPTS_DIR / "languages.md"

    base = base_path.read_text(encoding="utf-8") if base_path.exists() else "You are SAMVED voice assistant."
    safety = safety_path.read_text(encoding="utf-8") if safety_path.exists() else ""
    lang = lang_path.read_text(encoding="utf-8") if lang_path.exists() else ""

    return f"{base}\n\n{safety}\n\n{lang}".strip()