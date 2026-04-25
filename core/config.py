import tomllib
from pathlib import Path

_USER_CONFIG_DIR = Path.home() / ".config" / "steam-family-collections"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "steam-family-collections"
GAMES_FILE = DATA_DIR / "games.json"
CHILDREN_DIR = DATA_DIR / "children"

_EXAMPLE = """\
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"
# user_id = "12345678"  # optional; auto-detected when only one account exists

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
"""

_PLACEHOLDER_PREFIX = "YOUR_"


class ConfigError(Exception):
    pass


def _find_config_path() -> Path | None:
    local = Path.cwd() / "config.toml"
    if local.exists():
        return local
    if _USER_CONFIG_PATH.exists():
        return _USER_CONFIG_PATH
    return None


def load_config() -> dict:
    config_path = _find_config_path()
    if config_path is None:
        _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _USER_CONFIG_PATH.write_text(_EXAMPLE)
        raise ConfigError(
            f"Config file created at {_USER_CONFIG_PATH}\nFill in your API keys and run again."
        )

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    for section, key in [
        ("steam", "api_key"),
        ("steam", "steam_id"),
        ("mobygames", "api_key"),
    ]:
        val = config.get(section, {}).get(key, "")
        if not val or str(val).startswith(_PLACEHOLDER_PREFIX):
            raise ConfigError(f"Missing or unconfigured: [{section}] {key} in {config_path}")

    return config


def get_user_id(config: dict) -> str:
    user_id = config.get("steam", {}).get("user_id")
    if user_id:
        return str(user_id)

    userdata = Path.home() / ".local" / "share" / "Steam" / "userdata"
    if not userdata.exists():
        raise ConfigError("Steam userdata directory not found: ~/.local/share/Steam/userdata/")

    dirs = [d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit()]
    if not dirs:
        raise ConfigError("No Steam user directories found in ~/.local/share/Steam/userdata/")
    if len(dirs) > 1:
        names = ", ".join(d.name for d in sorted(dirs))
        raise ConfigError(
            f"Multiple Steam user directories found: {names}\nSet [steam] user_id in {CONFIG_PATH}"
        )
    return dirs[0].name
