from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./edge_alert.db"
    upload_dir: str = "uploads"
    anomaly_high_total_multiplier: float = 1.6
    anomaly_new_vendor_threshold: float = 75.0
    similarity_match_threshold: float = 0.35

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
