#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инвестиционный агент — анализ одного тикера.
Совместимость со старой командой: python agent.py --ticker LMT

Вся логика вынесена в пакет core/. Многотикерный режим — в terminal.py.
"""
import argparse, sys

from core.data       import get_data, get_history
from core.scoring    import calculate_score
from core.fair_value import calculate_fair_value
from core.signals    import generate_signal
from core.technical  import calculate_technical
from core.news       import get_news
from core.report     import generate_report
from core.db         import init_db, save_signal


def main():
    p = argparse.ArgumentParser(
        description="Инвестиционный агент анализа акций",
        epilog="Пример: python agent.py --ticker LMT",
    )
    p.add_argument("--ticker", required=True, type=str,
                   help="Тикер (AAPL, LMT, MSFT, BTC-USD)")
    p.add_argument("--no-cache", action="store_true",
                   help="Игнорировать кэш и загрузить свежие данные")
    args = p.parse_args()
    ticker = args.ticker.strip().upper()

    init_db()

    print(f"\U0001f4e1 Загружаю данные для {ticker}...")
    try:
        data = get_data(ticker, use_cache=not args.no_cache)
    except ConnectionError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных: {e}")
        sys.exit(1)

    print(f"✅ {data['name']}")

    print("\U0001f9ee Считаю скоринг...")
    score = calculate_score(data)

    print("\U0001f4d0 Считаю справедливую стоимость...")
    fv = calculate_fair_value(data)

    print("⚡ Формирую сигнал...")
    sig = generate_signal(data, score, fv)

    print("\U0001f4c8 Считаю технические индикаторы...")
    tech = calculate_technical(get_history(ticker))

    print("\U0001f4f0 Загружаю новости...")
    news = get_news(ticker)

    save_signal(ticker, score["total"], sig["signal"],
                fv.get("upside"), data.get("price"))

    generate_report(data, score, fv, sig, news, tech)


if __name__ == "__main__":
    main()
