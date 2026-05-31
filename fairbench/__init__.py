"""FairBench — voice competency training with integrity auditing."""

from pathlib import Path

__version__ = "0.1.0"

# Load .env into os.environ as early as possible. pydantic-settings populates the
# server Settings object but NOT os.environ, and the Pipecat bot reads secrets
# straight from os.environ (e.g. os.environ["GRADIUM_API_KEY"] in the TTS
# factory). Without this the live voice pipeline crashes with a KeyError the
# moment a call starts. python-dotenv ships with the [bot] extra; tolerate its
# absence for server/dev-only installs.
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:  # noqa: BLE001 - never let env loading break imports
    pass
