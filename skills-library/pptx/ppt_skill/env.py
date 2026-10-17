"""Environment variable loading."""

from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Load .env from the project root if present, else fall back to system env."""
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
