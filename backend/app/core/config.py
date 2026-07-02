import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    mongo_url: Optional[str]
    db_name: str
    openai_api_key: Optional[str]
    emergent_llm_key: Optional[str]
    frontend_url: Optional[str]
    cors_origins: str

    @classmethod
    def from_environment(cls) -> "AppConfig":
        return cls(
            mongo_url=os.getenv("MONGO_URL"),
            db_name=os.getenv("DB_NAME", "myhostiq"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            emergent_llm_key=os.getenv("EMERGENT_LLM_KEY"),
            frontend_url=os.getenv("FRONTEND_URL"),
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
        )

    def has_ai_credentials(self) -> bool:
        return bool(self.openai_api_key or self.emergent_llm_key)
