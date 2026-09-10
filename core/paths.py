# -*- coding: utf-8 -*-
"""Пути к ресурсам и к записываемым данным.

В сборке PyInstaller (--onefile) код распаковывается во временную папку,
поэтому __file__ указывает не туда, где лежит exe, и писать рядом нельзя.
Читаемые ресурсы берём из распаковки, изменяемые данные — из папки профиля.
"""
import os, sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

# Ресурсы только для чтения (ui.html и прочее, что положено в сборку)
if FROZEN:
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    RESOURCE_DIR = Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "InvestTerminal"
    return Path(os.path.expanduser("~")) / ".local" / "share" / "invest-terminal"


# Изменяемые данные: база, вотчлист.
# В обычном запуске оставляем data/ рядом с проектом — так удобнее в разработке.
DATA_DIR = _user_data_dir() if FROZEN else (RESOURCE_DIR / "data")


def data_file(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / name


def resource(name: str) -> Path:
    return RESOURCE_DIR / name
