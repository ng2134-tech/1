#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка одного .exe с Python и всеми библиотеками внутри.

Запускать НА WINDOWS — PyInstaller не умеет собирать под Windows из-под Linux:

    python build.py

Результат: dist\\InvestTerminal.exe — самодостаточный файл, получателю
устанавливать ничего не нужно. Нужен рабочий интернет: котировки тянутся
из Yahoo Finance в момент запуска.
"""
import subprocess, sys, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "InvestTerminal"

# Пакеты, которые PyInstaller не находит сам: yfinance грузит часть модулей
# динамически, curl_cffi и certifi несут бинарники и файлы данных.
COLLECT = ["yfinance", "curl_cffi", "certifi"]
HIDDEN  = ["core.paths", "core.data", "core.db", "core.registry", "core.scoring",
           "core.fair_value", "core.signals", "core.technical", "core.news",
           "core.report", "terminal"]


def need(mod: str, pypi: str) -> bool:
    try:
        __import__(mod)
        return False
    except ImportError:
        print(f"  ✗ нет {pypi}   ->  https://pypi.org/project/{pypi}/#files")
        return True


def main():
    if os.name != "nt":
        print("Этот скрипт нужно запускать на Windows: PyInstaller собирает")
        print("exe только под ту систему, на которой работает сам.")
        return 1

    print("Проверяю зависимости...")
    missing  = need("PyInstaller", "pyinstaller")
    missing |= need("yfinance", "yfinance")
    missing |= need("pandas", "pandas")
    if missing:
        print("\nСкачайте .whl по ссылкам выше и поставьте:")
        print('  pip install "путь\\к\\файлу.whl" --no-deps '
              '--trusted-host pypi.org --trusted-host files.pythonhosted.org')
        return 1

    ui = HERE / "ui.html"
    if not ui.exists():
        print(f"Нет {ui} — собирать нечего.")
        return 1

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onefile", "--console", "--name", NAME,
           # ui.html кладём в корень сборки: core/paths.py ищет его там
           "--add-data", f"{ui}{os.pathsep}."]
    for pkg in COLLECT:
        cmd += ["--collect-all", pkg]
    for mod in HIDDEN:
        cmd += ["--hidden-import", mod]
    cmd.append(str(HERE / "web.py"))

    print("\nСобираю (несколько минут, ~150 МБ на выходе)...\n")
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        print("\nСборка не удалась — смотрите вывод PyInstaller выше.")
        return r.returncode

    exe = HERE / "dist" / (NAME + ".exe")
    print("\n" + "=" * 58)
    print(f"  Готово: {exe}")
    print(f"  Размер: {exe.stat().st_size / 1e6:.0f} МБ" if exe.exists() else "  exe не найден")
    print("  Этот файл можно передавать как есть.")
    print("=" * 58)
    print("\nЕсли антивирус ругается — так бывает с однофайловыми сборками:")
    print("они распаковываются во временную папку, и эвристики принимают")
    print("это за угрозу. Помогает подпись сертификатом или сборка")
    print("без --onefile (папка вместо одного файла).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
