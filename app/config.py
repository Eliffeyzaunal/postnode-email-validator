from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_path: Path = PROJECT_ROOT / "data" / "validator.db"
    disposable_domains_path: Path = PROJECT_ROOT / "data" / "disposable_domains.txt"
    role_accounts_path: Path = PROJECT_ROOT / "data" / "role_accounts.txt"
    domain_typos_path: Path = PROJECT_ROOT / "data" / "domain_typos.json"
    dns_timeout_seconds: float = 2.0
    dns_cache_ttl_seconds: int = 86_400
    dns_error_cache_ttl_seconds: int = 300
    max_batch_size: int = 10_000
    max_upload_bytes: int = 5 * 1024 * 1024
    domain_concentration_threshold: float = 0.70
    domain_concentration_min_list_size: int = 100
    max_dns_workers: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

