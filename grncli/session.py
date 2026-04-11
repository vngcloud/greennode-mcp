from __future__ import annotations

import configparser
import os
from typing import Any

from grncli.emitter import HierarchicalEmitter

REGIONS = {
    "HCM-3": {
        "vks_endpoint": "https://vks.api.vngcloud.vn",
        "vserver_endpoint": "https://hcm-3.api.vngcloud.vn/vserver/vserver-gateway",
    },
    "HAN": {
        "vks_endpoint": "https://vks-han-1.api.vngcloud.vn",
        "vserver_endpoint": "https://han-1.api.vngcloud.vn/vserver/vserver-gateway",
    },
}

IAM_TOKEN_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"

ENV_VAR_MAP = {
    'region': 'GRN_DEFAULT_REGION',
    'output': 'GRN_DEFAULT_OUTPUT',
}

DEFAULT_CONFIG_DIR = os.path.expanduser('~/.greenode')


class Session:
    """Manages config, credentials, region, and service endpoints.

    Credential resolution order (high → low priority):
    1. Environment variables: GRN_CLIENT_ID, GRN_CLIENT_SECRET
    2. Profile in ~/.greenode/credentials
    """

    def __init__(
        self,
        config_dir: str | None = None,
        profile: str | None = None,
    ):
        self._config_dir = config_dir or DEFAULT_CONFIG_DIR
        self._profile = profile or os.environ.get('GRN_PROFILE', 'default')
        self._credentials_cache: dict[str, str] | None = None
        self._config_cache: dict[str, str] | None = None
        self._emitter = HierarchicalEmitter()
        self._token_manager = None
        self._region_override: str | None = None
        self._endpoint_override: str | None = None
        self.verify_ssl: bool = True
        self._read_timeout: int | None = None
        self._connect_timeout: int | None = None

    @property
    def profile(self) -> str:
        return self._profile

    @profile.setter
    def profile(self, value: str) -> None:
        self._profile = value
        self._credentials_cache = None
        self._config_cache = None

    def set_region_override(self, region: str) -> None:
        self._region_override = region

    def set_endpoint_override(self, endpoint: str) -> None:
        self._endpoint_override = endpoint

    def set_timeouts(
        self,
        read: int | None = None,
        connect: int | None = None,
    ) -> None:
        if read is not None:
            self._read_timeout = read
        if connect is not None:
            self._connect_timeout = connect

    def get_timeout(self) -> httpx.Timeout:
        import httpx
        read = self._read_timeout if self._read_timeout is not None else 30
        connect = self._connect_timeout if self._connect_timeout is not None else 30
        return httpx.Timeout(read=read, connect=connect, write=30, pool=30)

    @property
    def emitter(self) -> HierarchicalEmitter:
        return self._emitter

    def register(self, event_name: str, handler) -> None:
        self._emitter.register(event_name, handler)

    def emit(self, event_name: str, **kwargs) -> list:
        return self._emitter.emit(event_name, **kwargs)

    def emit_first_non_none(self, event_name: str, **kwargs) -> Any:
        return self._emitter.emit_first_non_none(event_name, **kwargs)

    def get_credentials(self) -> dict[str, str]:
        env_id = os.environ.get('GRN_CLIENT_ID')
        env_secret = os.environ.get('GRN_CLIENT_SECRET')
        if env_id and env_secret:
            return {'client_id': env_id, 'client_secret': env_secret}

        if self._credentials_cache is not None:
            return self._credentials_cache

        creds_file = os.path.join(self._config_dir, 'credentials')
        if not os.path.isfile(creds_file):
            raise FileNotFoundError(
                f"Credentials file not found: {creds_file}\n"
                f"Run 'grn configure' to set up credentials."
            )

        parser = configparser.ConfigParser()
        parser.read(creds_file)

        section = self._profile
        if not parser.has_section(section):
            raise ValueError(
                f"Profile '{section}' does not exist in {creds_file}"
            )

        try:
            client_id = parser.get(section, 'client_id')
            client_secret = parser.get(section, 'client_secret')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(
                f"Missing credentials for profile '{section}': {e}"
            ) from e

        self._credentials_cache = {
            'client_id': client_id,
            'client_secret': client_secret,
        }
        return self._credentials_cache

    def _load_config(self) -> dict[str, str]:
        if self._config_cache is not None:
            return self._config_cache

        config_file = os.path.join(self._config_dir, 'config')
        config = {}

        if os.path.isfile(config_file):
            parser = configparser.ConfigParser()
            parser.read(config_file)

            if self._profile == 'default':
                section = 'default'
            else:
                section = f'profile {self._profile}'

            if parser.has_section(section):
                config = dict(parser.items(section))
            elif self._profile == 'default' and parser.defaults():
                config = dict(parser.defaults())

        self._config_cache = config
        return self._config_cache

    def get_config_variable(self, name: str) -> str | None:
        if name == 'region' and self._region_override:
            return self._region_override

        env_var = ENV_VAR_MAP.get(name)
        if env_var:
            env_val = os.environ.get(env_var)
            if env_val:
                return env_val

        config = self._load_config()
        return config.get(name)

    def get_scoped_config(self) -> dict[str, str]:
        return dict(self._load_config())

    def get_region(self) -> str:
        region = self.get_config_variable('region')
        if not region:
            raise ValueError(
                "Region is not configured. "
                "Use 'grn configure' or the --region flag."
            )
        return region

    def get_endpoint(self, service_name: str) -> str:
        if self._endpoint_override:
            return self._endpoint_override

        region = self.get_region()
        region_config = REGIONS.get(region)
        if not region_config:
            raise ValueError(f"Invalid region: {region}")

        endpoint_key = f'{service_name}_endpoint'
        endpoint = region_config.get(endpoint_key)
        if not endpoint:
            raise ValueError(
                f"Endpoint not found for service '{service_name}' "
                f"in region '{region}'"
            )
        return endpoint

    def get_token_manager(self):
        if self._token_manager is None:
            from grncli.auth import TokenManager
            creds = self.get_credentials()
            self._token_manager = TokenManager(
                client_id=creds['client_id'],
                client_secret=creds['client_secret'],
            )
        return self._token_manager

    def create_client(self, service_name: str):
        from grncli.client import GreenodeClient
        return GreenodeClient(self, service_name)

    @property
    def config_dir(self) -> str:
        return self._config_dir

    @property
    def credentials_file(self) -> str:
        return os.path.join(self._config_dir, 'credentials')

    @property
    def config_file(self) -> str:
        return os.path.join(self._config_dir, 'config')
