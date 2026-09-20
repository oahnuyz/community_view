"""Keep both service secrets outside experiment and model configuration snapshots."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, SecretStr


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chat_api_key: SecretStr
    embedding_api_key: SecretStr

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            raise ValueError(
                f"Create credentials file {path} with chat_api_key and embedding_api_key"
            )
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

    def key(self, purpose):
        value = self.embedding_api_key if purpose == "embedding" else self.chat_api_key
        key = value.get_secret_value().strip()
        if not key:
            raise ValueError(
                f"Fill {'embedding_api_key' if purpose == 'embedding' else 'chat_api_key'} in credentials file"
            )
        return key
