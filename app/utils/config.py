"""Configuration management for the Insurance Claims Agent."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration sourced from env vars with config.json fallback."""

    def __init__(self):
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
        else:
            self.config_data = {}

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

    # --- Helpers ---
    def is_api_key_configured(self) -> bool:
        """True if an OpenAI API key is present. Lets callers fail clearly."""
        return bool(self.openai_api_key.strip())


# Global config instance
config = Config()
