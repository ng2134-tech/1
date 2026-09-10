#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инвестиционный терминал — многотикерный режим.

  python terminal.py                 # дашборд по вотчлисту
  python terminal.py --ticker LMT    # полный анализ одного тикера
  python terminal.py --add NVDA      # добавить в вотчлист
  python terminal.py --remove NVDA   # убрать из вотчлиста
"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from core.data       import get_data, get_history
from core.scoring    import calculate_score
from core.fair_value import calculate_fair_value
from core.signals    import generate_signal
from core.technical  import calculate_technical
from core.news       import get_news
from core.report     import generate_report
from core.db         import init_db, save_signal
from core.registry   import REGISTRY

WATCHLIST_PATH = Path(__file__).parent / "data" / "watchlist.json"
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "LMT", "NVDA", "BTC-USD"]


# ── вотчлист ────────────────────────────────────────────────────
def load_watchlist() -> list:
    if WATCHLIST_PATH.exists():
        try:
            return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    save_watchlist(DEFAULT_WATCHLIST)
    return list(DEFAULT_WATCHLIST)

def save_watchlist(tickers: list):
    WATCHLIST_PATH.parent.mkdir(exist_ok=True)
    # \n в конце — иначе каждый --add/--remove даёт лишний diff в git
    WATCHLIST_PATH.write_text(json.dumps(tickers, indent=2) + "\n", encoding="utf-8")


# ── анализ одного тикера (для параллельного запуска) ────────────
def analyze(ticker: str) -> dict:
    """Возвращает сводку по тикеру. Ошибки не бросает — кладёт в 'error'."""
    try:
        data  = get_data(ticker)
        score = calculate_score(data)
        fv    = calculate_fair_value(data)
        sig   = generate_signal(data, score, fv)
        save_signal(ticker, score["total"], sig["signal"],
                    fv.get("upside"), data.get("price"))
        return {
            "ticker": ticker, "ok": True,
            "name": data.get("name", ""), "price": data.get("price"),
            "score": score["total"], "rating": score["rating"],
            "fv": fv.get("fair_value"), "upside": fv.get("upside"),
            "signal": sig["signal"], "warnings": sig["warnings"],
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)[:160]}


# ── дашборд ─────────────────────────────────────────────────────
def short_signal(sig: str) -> str:
    """Укорачивает сигнал до колонки таблицы."""
    for key, out in [("СИЛЬНЫЙ ЛОНГ", "📈 СИЛ.ЛОНГ"), ("ПОТЕНЦИАЛЬНЫЙ ЛОНГ", "📈 ЛОНГ"),
                     ("ДЕРЖАТЬ", "⚖️  ДЕРЖАТЬ"), ("СИЛЬНЫЙ ШОРТ", "📉 СИЛ.ШОРТ"),
                     ("ПОТЕНЦ. ШОРТ", "📉 ШОРТ"), ("НАБЛЮДАТЬ", "👀 НАБЛЮД.")]:
        if key in sig:
            return out
    return sig[:12]

def print_dashboard(results: list):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print("\n" + "═" * 78)
    print(f"  🔍 ИНВЕСТИЦИОННЫЙ ТЕРМИНАЛ{' ' * 28}{now}")
    print("═" * 78)
    print(f"  {'Тикер':<9}{'Цена':>11}{'Скоринг':>9}{'Fair Value':>13}{'Апсайд':>9}  Сигнал")
    print("─" * 78)

    for r in results:
        if not r["ok"]:
            print(f"  {r['ticker']:<9}{'—':>11}{'—':>9}{'—':>13}{'—':>9}  ❌ {r['error']}")
            continue
        price  = f"${r['price']:.2f}" if r["price"] else "—"
        fv     = f"${r['fv']:.2f}" if r["fv"] else "—"
        upside = f"{r['upside']:+.1f}%" if r["upside"] is not None else "—"
        print(f"  {r['ticker']:<9}{price:>11}{r['score']:>9}{fv:>13}{upside:>9}  {short_signal(r['signal'])}")

    print("─" * 78)

    # Предупреждения по всем тикерам
    warns = [(r["ticker"], w) for r in results if r["ok"] for w in r.get("warnings", [])]
    if warns:
        print("  ⚡ ПРЕДУПРЕЖДЕНИЯ")
        for tk, w in warns[:6]:
            print(f"     {tk:<8} {w}")
        print("─" * 78)

    # Статус источников данных (capability registry)
    for topic, sources in REGISTRY.status().items():
        line = "  ".join(f"{s['name']}={'ok' if s['ok'] else 'сбой'}" for s in sources)
        print(f"  Источники [{topic}]: {line}")
    print("═" * 78)
    print("  python terminal.py --ticker <ТИКЕР>  — полный анализ")
    print("  Это аналитический инструмент, не инвестиционный совет.\n")


# ── полный анализ одного тикера ─────────────────────────────────
def full_analysis(ticker: str):
    print(f"📡 Загружаю данные для {ticker}...")
    try:
        data = get_data(ticker)
    except ConnectionError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

    print(f"✅ {data['name']}")
    print("🧮 Считаю скоринг...")
    score = calculate_score(data)
    print("📐 Считаю справедливую стоимость...")
    fv  = calculate_fair_value(data)
    sig = generate_signal(data, score, fv)
    print("📈 Считаю технические индикаторы...")
    tech = calculate_technical(get_history(ticker))
    print("📰 Загружаю новости...")
    news = get_news(ticker)

    save_signal(ticker, score["total"], sig["signal"], fv.get("upside"), data.get("price"))
    generate_report(data, score, fv, sig, news, tech)


def main():
    p = argparse.ArgumentParser(description="Инвестиционный терминал")
    p.add_argument("--ticker", type=str, help="Полный анализ одного тикера")
    p.add_argument("--add",    type=str, help="Добавить тикер в вотчлист")
    p.add_argument("--remove", type=str, help="Убрать тикер из вотчлиста")
    args = p.parse_args()

    init_db()
    wl = load_watchlist()

    if args.add:
        t = args.add.strip().upper()
        if t not in wl:
            wl.append(t); save_watchlist(wl)
            print(f"✅ {t} добавлен. Вотчлист: {', '.join(wl)}")
        else:
            print(f"⚠️  {t} уже в вотчлисте")
        return

    if args.remove:
        t = args.remove.strip().upper()
        if t in wl:
            wl.remove(t); save_watchlist(wl)
            print(f"✅ {t} убран. Вотчлист: {', '.join(wl)}")
        else:
            print(f"⚠️  {t} не найден в вотчлисте")
        return

    if args.ticker:
        full_analysis(args.ticker.strip().upper())
        return

    # Дашборд: параллельная загрузка всех тикеров вотчлиста
    print(f"📡 Загружаю {len(wl)} тикеров...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(analyze, wl))
    print_dashboard(results)


if __name__ == "__main__":
    main()
