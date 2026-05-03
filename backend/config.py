from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_host: str = "http://127.0.0.1:11434"
    model: str = "llama3.1:8b"
    ollama_timeout: float = 60.0

    temperature: float = 0.85
    top_p: float = 0.9

    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
