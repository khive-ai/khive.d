from typing import Any, ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseKhiveSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".secrets.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        check_fields=False,
    )

    # Class variable to store the singleton instance
    _instance: ClassVar[Any] = None

    def get_secret(self, key_name: str) -> str:
        """Get the secret value for a given key name."""
        if not hasattr(self, key_name):
            raise AttributeError(f"Secret key '{key_name}' not found in settings")
        secret = getattr(self, key_name)
        if secret is None:
            raise ValueError(f"Secret key '{key_name}' is not set")

        if isinstance(secret, SecretStr):
            return secret.get_secret_value()

        return str(secret)


# # Create a singleton instance
# settings = BaseKhiveToolkitConfig()
# # Store the instance in the class variable for singleton pattern
# BaseKhiveToolkitConfig._instance = settings
