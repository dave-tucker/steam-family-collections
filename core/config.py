import tomllib
from pathlib import Path

_USER_CONFIG_DIR = Path.home() / ".config" / "steam-family-collections"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "steam-family-collections"
GAMES_FILE = DATA_DIR / "games.json"
CHILDREN_DIR = DATA_DIR / "children"

DEMO_MODE: bool = False
_DEMO_DIR = Path(__file__).parent.parent / "demo"


def enable_demo_mode() -> None:
    global DEMO_MODE, DATA_DIR, GAMES_FILE, CHILDREN_DIR
    DEMO_MODE = True
    DATA_DIR = _DEMO_DIR
    GAMES_FILE = _DEMO_DIR / "games.json"
    CHILDREN_DIR = _DEMO_DIR / "children"


_EXAMPLE = """\
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"
# user_id = "12345678"  # optional; auto-detected when only one account exists

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
"""

_PLACEHOLDER_PREFIX = "YOUR_"

_STEAM_DIR_CANDIDATES = [
    Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam",  # Flatpak (preferred)
    Path.home() / ".local/share/Steam",  # native
]


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

    if config.get("app", {}).get("demo", False):
        enable_demo_mode()
        return config

    for section, key in [
        ("steam", "api_key"),
        ("steam", "steam_id"),
        ("mobygames", "api_key"),
    ]:
        val = config.get(section, {}).get(key, "")
        if not val or str(val).startswith(_PLACEHOLDER_PREFIX):
            raise ConfigError(f"Missing or unconfigured: [{section}] {key} in {config_path}")

    return config


def get_steam_dir(config: dict) -> Path:
    """Return the Steam data directory from config or by auto-detection."""
    configured = config.get("steam", {}).get("path")
    if configured:
        return Path(configured)
    for candidate in _STEAM_DIR_CANDIDATES:
        if candidate.exists():
            return candidate
    return _STEAM_DIR_CANDIDATES[0]


def get_user_id(config: dict) -> str:
    user_id = config.get("steam", {}).get("user_id")
    if user_id:
        return str(user_id)

    steam_dir = get_steam_dir(config)
    userdata = steam_dir / "userdata"
    if not userdata.exists():
        raise ConfigError(f"Steam userdata directory not found: {userdata}")

    dirs = [d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit()]
    if not dirs:
        raise ConfigError(f"No Steam user directories found in {userdata}")
    if len(dirs) > 1:
        names = ", ".join(d.name for d in sorted(dirs))
        raise ConfigError(
            f"Multiple Steam user directories found: {names}\n"
            f"Set [steam] user_id in {_USER_CONFIG_PATH}"
        )
    return dirs[0].name
