from pathlib import Path
import os

from dotenv import load_dotenv


def load_instruction_from_file(file_path):
    # __file__ đang là vị trí của util.py
    # os.path.dirname(__file__) sẽ là thư mục utils
    # os.path.dirname(...) lần nữa sẽ lùi ra thư mục gốc Shopping_Research_Agent
    base_dir = os.path.dirname(os.path.dirname(__file__))

    # Ghép path chuẩn
    full_path = os.path.join(base_dir, file_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Instruction file not found: {full_path}")

    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


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
