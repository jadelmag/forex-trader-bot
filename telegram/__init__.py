"""Telegram package initializer.
Carga TelegramNotifier desde 'telegram-notifier.py' usando importlib ya que el nombre del archivo contiene un guion.
"""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

_this_dir = Path(__file__).parent
_module_path = _this_dir / "telegram-notifier.py"

TelegramNotifier = None  # será asignado dinámicamente
if _module_path.exists():
    spec = spec_from_file_location("telegram_notifier", str(_module_path))
    if spec and spec.loader:
        _mod = module_from_spec(spec)
        spec.loader.exec_module(_mod)  # type: ignore[attr-defined]
        TelegramNotifier = getattr(_mod, "TelegramNotifier", None)
        del _mod

__all__ = ["TelegramNotifier"]
