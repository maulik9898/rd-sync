import argparse
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple, Type

import yaml
from platformdirs import user_config_dir
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class LogSettings(BaseModel):
    """Logging-related settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class APISettings(BaseModel):
    """API-related settings."""

    base_url: str = "https://api.real-debrid.com/rest/1.0"
    rate_limit_per_minute: int = 250
    torrents_rate_limit_per_minute: int = 75
    timeout_secs: int = 60
    fetch_torrents_page_size: int = 2000
    disable_httpx_logging: bool = True


class RDAccount(BaseModel):
    """Real-Debrid account configuration."""

    token: str
    description: Optional[str] = None


class SyncSchedule(BaseModel):
    """Schedule configuration for a sync job."""

    type: Literal["interval", "cron"]
    value: str | int  # int for interval (seconds), str for cron expression


class SyncConfig(BaseModel):
    """Configuration for a sync job."""

    source: str
    destination: str
    schedule: SyncSchedule
    enabled: bool = True
    dry_run: bool = False


class YAMLConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads from YAML file."""

    def __init__(
        self, settings_cls: Type[BaseSettings], yaml_path: Optional[Path] = None
    ) -> None:
        super().__init__(settings_cls)
        self.yaml_path = yaml_path

    def get_config_path(self) -> Path:
        """Get config file path, checking CLI arg and default locations."""
        # First check if path provided via CLI
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config", type=Path, help="Path to config file")
        args, _ = parser.parse_known_args()

        if args.config:
            if not args.config.exists():
                raise FileNotFoundError(f"Config file not found: {args.config}")
            return args.config

        # If no CLI path, check default location
        default_path = Path(user_config_dir("rd-sync")) / "config.yaml"
        if not default_path.exists():
            raise FileNotFoundError(
                f"No config file found at CLI path or default path: {default_path}"
            )
        return default_path

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        """Get value for a field from YAML config."""
        try:
            config_path = self.yaml_path or self.get_config_path()
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
                field_value = yaml_data.get(field_name)
                return field_value, field_name, False
        except Exception:
            return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """Load complete config from YAML file."""
        try:
            config_path = self.yaml_path or self.get_config_path()
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
                return yaml_data
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}") from e


class Settings(BaseSettings):
    """Application settings."""

    api: APISettings = APISettings()
    log: LogSettings = LogSettings()
    accounts: Dict[str, RDAccount] = {}
    syncs: Dict[str, SyncConfig] = {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources.

        Order of precedence:
        1. init_settings (values passed to Settings())
        2. yaml_settings (from config file)
        """
        yaml_settings = YAMLConfigSettingsSource(settings_cls)
        return init_settings, yaml_settings

    @property
    def api_base_url(self) -> str:
        return self.api.base_url

    @property
    def api_rate_limit_per_minute(self) -> int:
        return self.api.rate_limit_per_minute

    @property
    def torrents_rate_limit_per_minute(self) -> int:
        return self.api.torrents_rate_limit_per_minute

    @property
    def api_timeout_secs(self) -> int:
        return self.api.timeout_secs

    @property
    def fetch_torrents_page_size(self) -> int:
        return self.api.fetch_torrents_page_size

    @property
    def disable_httpx_logging(self) -> bool:
        return self.api.disable_httpx_logging
