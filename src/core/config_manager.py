"""Configuration manager for GUI application.

Handles API keys, application settings, and secure storage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


class ConfigManager:
    """Manages application configuration with encrypted API key storage."""

    def __init__(self, config_dir: str | None = None):
        """Initialize configuration manager.

        Args:
            config_dir: Directory to store configuration files.
                       Defaults to ~/.xhs_agent/
        """
        if config_dir is None:
            config_dir = str(Path.home() / ".xhs_agent")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / ".key"

        self._cipher = self._init_cipher()
        self._config: dict[str, Any] = {}
        self.load_config()

    def _init_cipher(self) -> Fernet:
        """Initialize or load encryption cipher."""
        if self.key_file.exists():
            key = self.key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            # Make key file read-only for current user
            if os.name != "nt":  # Unix-like systems
                os.chmod(self.key_file, 0o600)

        return Fernet(key)

    def load_config(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
                self._config = self._get_default_config()
        else:
            self._config = self._get_default_config()

        return self._config

    def save_config(self, config: dict[str, Any] | None = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration dictionary to save.
                   If None, saves current config.
        """
        if config is not None:
            self._config = config

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}")

    def get_api_key(self, key_name: str) -> str:
        """Get decrypted API key.

        Args:
            key_name: Name of the API key (e.g., 'google', 'tavily')

        Returns:
            Decrypted API key or empty string if not found
        """
        encrypted = self._config.get("api_keys", {}).get(key_name, "")
        if not encrypted:
            return ""

        try:
            return self.decrypt_value(encrypted)
        except Exception:
            return ""

    def set_api_key(self, key_name: str, value: str) -> None:
        """Set API key with encryption.

        Args:
            key_name: Name of the API key (e.g., 'google', 'tavily')
            value: API key value to encrypt and store
        """
        if "api_keys" not in self._config:
            self._config["api_keys"] = {}

        if value:
            self._config["api_keys"][key_name] = self.encrypt_value(value)
        else:
            self._config["api_keys"].pop(key_name, None)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self._config.get("settings", ).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set application setting.

        Args:
            key: Setting key
            value: Setting value
        """
        if "settings" not in self._config:
            self._config["settings"] = {}

        self._config["settings"][key] = value

    def validate_config(self) -> tuple[bool, str]:
        """Validate configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required API keys
        google_key = self.get_api_key("google")
        tavily_key = self.get_api_key("tavily")

        if not google_key:
            return False, "Google API Key is required"

        if not tavily_key:
            return False, "Tavily API Key is required"

        return True, ""

    def encrypt_value(self, value: str) -> str:
        """Encrypt a string value.

        Args:
            value: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        return self._cipher.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted: Encrypted string (base64 encoded)

        Returns:
            Decrypted string
        """
        return self._cipher.decrypt(encrypted.encode()).decode()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "api_keys": {},
            "settings": {
                "gemini_model": "gemini-2.5-flash",
                "minimax_model": "MiniMax-M2.1",
                "minimax_base_url": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
                "analysis_temperature": 0.0,
                "rewrite_temperature": 0.7,
                "cover_temperature": 0.6,
                "max_results": 5,
                "max_queries": 6,
                "max_sources": 10,
                "days": 30,
                "lang": "zh",
                "region": "cn",
                "out_dir": "outputs",
                "cover_image_provider": "minimax",
                "cover_image_model": "image-01",
                "cover_image_aspect": "3:4",
            },
        }

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults (keeps API keys)."""
        api_keys = self._config.get("api_keys", {})
        self._config = self._get_default_config()
        self._config["api_keys"] = api_keys

    def export_for_env(self) -> dict[str, str]:
        """Export configuration as environment variables.

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}

        # API keys
        google_key = self.get_api_key("google")
        if google_key:
            env_vars["GOOGLE_API_KEY"] = google_key

        tavily_key = self.get_api_key("tavily")
        if tavily_key:
            env_vars["TAVILY_API_KEY"] = tavily_key

        minimax_key = self.get_api_key("minimax")
        if minimax_key:
            env_vars["MINIMAX_API_KEY"] = minimax_key

        # Settings with XHS_ prefix
        settings = self._config.get("settings", {})
        for key, value in settings.items():
            env_key = f"XHS_{key.upper()}"
            env_vars[env_key] = str(value)

        return env_vars
