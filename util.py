from pathlib import Path
import os

from dotenv import load_dotenv


def load_instruction_from_file(file_name: str) -> str:
    """Load a prompt file located next to this module."""
    base_dir = Path(__file__).resolve().parent
    instruction_path = base_dir / file_name

    if not instruction_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_path}")

    content = instruction_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Instruction file is empty: {instruction_path}")

    return content


def bootstrap_api_env() -> str | None:
    """Load .env and normalize API key env names for Google ADK."""
    base_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=base_dir / ".env", override=False)
    load_dotenv(override=False)

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key

    return os.getenv("GOOGLE_API_KEY")


def ensure_api_key_configured() -> str:
    """Return configured API key or raise a clear startup error."""
    api_key = bootstrap_api_env()
    if not api_key:
        raise RuntimeError(
            "Missing Gemini API key. Set GOOGLE_API_KEY (or GEMINI_API_KEY) in .env or your shell."
        )
    return api_key
