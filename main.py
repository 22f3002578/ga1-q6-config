
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

KEY_MAP = {
    "APP_PORT": "port",
    "APP_WORKERS": "workers",
    "APP_DEBUG": "debug",
    "APP_LOG_LEVEL": "log_level",
    "APP_API_KEY": "api_key",
    "NUM_WORKERS": "workers",
}


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in (
        "true", "1", "yes", "on"
    )


def convert(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}
            config.update(yaml_config)

    # Layer 3: .env file
    env_file = dotenv_values(".env")
    for key, value in env_file.items():
        normalized = KEY_MAP.get(key)
        if normalized and value is not None:
            config[normalized] = value

    # Layer 4: OS environment variables
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            normalized = KEY_MAP.get(key)
            if normalized:
                config[normalized] = value

    # Highest priority: CLI overrides through repeated set parameters
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        if key in config:
            config[key] = value

    # Convert values to the required types
    result = {
        key: convert(key, value)
        for key, value in config.items()
    }

    # Never expose the actual API key
    result["api_key"] = "*****"

    return result
