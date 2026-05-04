from typing import Any

from config import settings
from database import SessionLocal
from models.operational import PluginSetting


DEFAULT_CONTROLS = {
    "emergency_stop": False,
    "dry_run_tools": False,
    "max_tool_execution_ms": 5000,
}


def get_system_controls() -> dict[str, Any]:
    controls = dict(DEFAULT_CONTROLS)
    controls.update({
        "emergency_stop": settings.emergency_stop,
        "dry_run_tools": settings.dry_run_tools,
        "max_tool_execution_ms": settings.max_tool_execution_ms,
    })
    try:
        with SessionLocal() as db:
            row = db.query(PluginSetting).filter(PluginSetting.name == "system-controls").first()
            if row and isinstance(row.config, dict):
                controls.update(row.config)
    except Exception:
        pass
    return controls


def is_emergency_stop_enabled() -> bool:
    return bool(get_system_controls().get("emergency_stop"))


def is_dry_run_enabled() -> bool:
    return bool(get_system_controls().get("dry_run_tools"))


def max_tool_execution_ms() -> int:
    value = get_system_controls().get("max_tool_execution_ms", 5000)
    try:
        return max(1, int(value))
    except Exception:
        return 5000
