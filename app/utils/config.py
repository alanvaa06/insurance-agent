"""Configuration management for the Insurance Claims Agent."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration sourced from env vars with config.json fallback."""

    def __init__(self):
        config_path = Path("config.json")
        self.config_data = {}
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                # A malformed optional config file must not crash startup.
                print(f"Warning: ignoring invalid config.json: {e}", file=sys.stderr)

    # --- API ---
    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY") or self.config_data.get("API_KEY", "")

    @property
    def openai_base_url(self) -> str:
        return os.getenv("OPENAI_BASE_URL") or self.config_data.get(
            "OPENAI_API_BASE", "https://api.openai.com/v1"
        )

    # --- Models ---
    @property
    def model_name(self) -> str:
        return os.getenv("MODEL_NAME", "gpt-4o-mini")

    @property
    def embedding_model(self) -> str:
        return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # --- ChromaDB ---
    @property
    def chroma_persist_directory(self) -> str:
        return os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    @property
    def chroma_collection_name(self) -> str:
        return os.getenv("CHROMA_COLLECTION", "insurance_policies")

    # --- Data paths ---
    @property
    def policy_pdf_path(self) -> str:
        return os.getenv("POLICY_PDF_PATH", "./data/policy.pdf")

    @property
    def coverage_csv_path(self) -> str:
        # Default matches the file actually shipped in data/.
        return os.getenv("COVERAGE_CSV_PATH", "./data/coverage_data.csv")

    # --- Business rules ---
    @property
    def high_amount_threshold(self) -> float:
        try:
            return float(os.getenv("HIGH_AMOUNT_THRESHOLD", "10000"))
        except ValueError:
            return 10000.0

    @property
    def llm_timeout_seconds(self) -> float:
        try:
            return float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
        except ValueError:
            return 30.0

    @property
    def llm_max_retries(self) -> int:
        try:
            return int(os.getenv("LLM_MAX_RETRIES", "2"))
        except ValueError:
            return 2

    # --- Helpers ---
    def is_api_key_configured(self) -> bool:
        """True if an OpenAI API key is present. Lets callers fail clearly."""
        return bool(self.openai_api_key.strip())


# Global config instance
config = Config()
