#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инвестиционный агент анализа акций
Использование: python agent.py --ticker LMT
"""

import argparse
import sys
from datetime import datetime
import xml.etree.ElementTree as ET

try:
    import yfinance as yf
except ImportError:
    print("❌ Установите зависимости: pip install yfinance requests pandas")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None

try:
    import pandas as pd
except ImportError:
    pd = None


# ─────────────────────────────────────────────
# МОДУЛЬ 1: СБОР ДАННЫХ
# ─────────────────────────────────────────────

def get_data(ticker: str) -> dict:
    """Загружает все необходимые данные по тикеру через yfinance."""
    print(f"📡 Загружаю данные для {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Проверка: если компания не найдена, поле shortName/longName будет пустым
        name = info.get("longName") or info.get("shortName")
        if not name:
            print(f"❌ Тикер '{ticker}' не найден. Проверьте правильность ввода.")
            sys.exit(1)

        print(f"✅ {name}")

        # Хелпер для безопасного извлечения значений
        def g(key):
            val = info.get(key)
            return val if val not in (None, "N/A", 0.0) or key in ("dividendYield", "dividendRate") else None

        # D/E: yfinance возвращает в процентах, делим на 100
        raw_de = info.get("debtToEquity")
        de_ratio = (raw_de / 100) if raw_de is not None else None

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        shares = (market_cap / price) if (market_cap and price) else None

        data = {
            "ticker": ticker.upper(),
            "name": name,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "price": price,
            "market_cap": market_cap,
            "beta": info.get("beta"),
            "pe": info.get("trailingPE"),
            "ps": info.get("priceToSalesTrailing12Months"),
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "ev_sales": info.get("enterpriseToRevenue"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "de": de_ratio,
            "margin": info.get("profitMargins"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "fcf": info.get("freeCashflow"),
            "revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
            "total_debt": info.get("totalDebt"),
            "div_yield": info.get("dividendYield"),
            "div_rate": info.get("dividendRate"),
            "short_pct": info.get("shortPercentOfFloat"),
            "target_price": info.get("targetMeanPrice"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "shares": shares,
        }
        return data

    except Exception as e:
        err = str(e)
        if "proxy" in err.lower() or "tunnel" in err.lower() or "403" in err or "curl" in err.lower():
            print("❌ Нет доступа к интернету. Проверьте подключение или настройки прокси.")
        elif "Failed to perform" in err:
            print(f"❌ Ошибка сети: {err}")
        else:
            print(f"❌ Ошибка при загрузке данных: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────
# МОДУЛЬ 2: СКОРИНГОВАЯ СИСТЕМА
# ─────────────────────────────────────────────

def score_pe(pe):
    """Скоринг P/E мультипликатора."""
    if pe is None or pe <= 0:
        return 0, "N/A"
    if pe < 10:
        return 1000, "Очень низкий ✅"
    if pe < 15:
        return 900, "Низкий ✅"
    if pe < 25:
        return 750, "Умеренный ⚠️"
    if pe < 35:
        return 500, "Высокий ⚠️"
    return 300, "Очень высокий ❌"


def score_ps(ps):
    """Скоринг P/S мультипликатора."""
    if ps is None:
        return 0, "N/A"
    if ps < 1:
        return 1000, "Очень низкий ✅"
    if ps < 2:
        return 900, "Низкий ✅"
    if ps < 4:
        return 700, "Умеренный ⚠️"
    if ps < 8:
        return 450, "Высокий ⚠️"
    return 250, "Очень высокий ❌"


def score_ev_ebitda(ev):
    """Скоринг EV/EBITDA мультипликатора."""
    if ev is None or ev <= 0:
        return 0, "N/A"
    if ev < 8:
        return 1000, "Очень низкий ✅"
    if ev < 12:
        return 880, "Низкий ✅"
    if ev < 18:
        return 700, "Умеренный ⚠️"
    if ev < 25:
        return 450, "Высокий ⚠️"
    return 250, "Очень высокий ❌"


def score_roe(roe):
    """Скоринг ROE."""
    if roe is None:
        return 0, "N/A"
    pct = roe * 100
    if pct > 30:
        return 1000, "Высокий ✅"
    if pct > 20:
        return 900, "Хороший ✅"
    if pct > 10:
        return 700, "Средний ⚠️"
    if pct > 0:
        return 400, "Низкий ⚠️"
    return 100, "Отрицательный ❌"


def score_roa(roa):
    """Скоринг ROA."""
    if roa is None:
        return 0, "N/A"
    pct = roa * 100
    if pct > 15:
        return 1000, "Высокий ✅"
    if pct > 10:
        return 850, "Хороший ✅"
    if pct > 5:
        return 700, "Средний ⚠️"
    if pct > 0:
        return 400, "Низкий ⚠️"
    return 100, "Отрицательный ❌"


def score_de(de):
    """Скоринг D/E коэффициента."""
    if de is None:
        return 0, "N/A"
    if de < 0.3:
        return 1000, "Очень низкий ✅"
    if de < 1:
        return 900, "Низкий ✅"
    if de < 2:
        return 750, "Умеренный ⚠️"
    if de < 3.5:
        return 500, "Высокий ⚠️"
    return 200, "Очень высокий ❌"


def score_margin(margin):
    """Скоринг чистой маржи."""
    if margin is None:
        return 0, "N/A"
    pct = margin * 100
    if pct > 25:
        return 1000, "Очень высокая ✅"
    if pct > 15:
        return 900, "Высокая ✅"
    if pct > 10:
        return 750, "Хорошая ✅"
    if pct > 5:
        return 550, "Средняя ⚠️"
    if pct > 0:
        return 300, "Низкая ⚠️"
    return 50, "Отрицательная ❌"


def score_short(short_pct):
    """Бонус/штраф за Short Interest."""
    if short_pct is None:
        return 0, "N/A"
    pct = short_pct * 100
    if pct < 2:
        return 200, "Низкий шорт ✅"
    if pct < 5:
        return 100, "Нормальный"
    if pct < 10:
        return -100, "Повышенный ⚠️"
    return -300, "Высокий шорт ❌"


def get_rating(score):
    """Возвращает рейтинговую метку по итоговому баллу."""
    if score >= 6500:
        return "ОТЛИЧНАЯ ОЦЕНКА ✅✅"
    if score >= 5000:
        return "ХОРОШАЯ ОЦЕНКА ✅"
    if score >= 3500:
        return "СРЕДНЯЯ ОЦЕНКА ⚠️"
    if score >= 2000:
        return "СЛАБАЯ ОЦЕНКА ❌"
    return "ОЧЕНЬ СЛАБАЯ ОЦЕНКА ❌❌"


def calculate_score(data: dict) -> dict:
    """Считает скоринг по всем метрикам."""
    print("🧮 Считаю скоринг...")

    pe_s, pe_c = score_pe(data["pe"])
    ps_s, ps_c = score_ps(data["ps"])
    ev_s, ev_c = score_ev_ebitda(data["ev_ebitda"])
    roe_s, roe_c = score_roe(data["roe"])
    roa_s, roa_c = score_roa(data["roa"])
    de_s, de_c = score_de(data["de"])
    mg_s, mg_c = score_margin(data["margin"])
    sh_s, sh_c = score_short(data["short_pct"])

    total = pe_s + ps_s + ev_s + roe_s + roa_s + de_s + mg_s + sh_s

    return {
        "pe": (pe_s, pe_c),
        "ps": (ps_s, ps_c),
        "ev_ebitda": (ev_s, ev_c),
        "roe": (roe_s, roe_c),
        "roa": (roa_s, roa_c),
        "de": (de_s, de_c),
        "margin": (mg_s, mg_c),
        "short": (sh_s, sh_c),
        "total": total,
        "rating": get_rating(total),
    }


# ─────────────────────────────────────────────
# МОДУЛЬ 3: РАСЧЁТ СПРАВЕДЛИВОЙ СТОИМОСТИ
# ─────────────────────────────────────────────

def calculate_fair_value(data: dict) -> dict:
    """Рассчитывает Fair Value тремя методами и строит сценарии."""
    print("📐 Считаю справедливую стоимость...")

    # CCA — используем таргет аналитиков или форвардный EPS × медианный P/E
    cca = data.get("target_price")
    if not cca:
        fwd_eps = data.get("eps_forward")
        if fwd_eps and fwd_eps > 0:
            cca = fwd_eps * 18  # дефолтный медианный P/E сектора

    # DCF упрощённый: forward_eps × 20 или trailing_eps × 18
    dcf = None
    if data.get("eps_forward") and data["eps_forward"] > 0:
        dcf = data["eps_forward"] * 20
    elif data.get("eps_trailing") and data["eps_trailing"] > 0:
        dcf = data["eps_trailing"] * 18

    # NAV через EV/EBITDA: (ebitda × 12 - total_debt) / shares
    nav = None
    ebitda = data.get("ebitda")
    total_debt = data.get("total_debt") or 0
    shares = data.get("shares")
    if ebitda and ebitda > 0 and shares and shares > 0:
        nav = (ebitda * 12 - total_debt) / shares

    # Взвешенное среднее: 40% CCA + 40% DCF + 20% NAV
    weights = []
    values = []
    if cca:
        weights.append(0.4)
        values.append(cca)
    if dcf:
        weights.append(0.4)
        values.append(dcf)
    if nav:
        weights.append(0.2)
        values.append(nav)

    if not values:
        fair_value = None
    else:
        # Нормализуем веса если не все методы доступны
        total_w = sum(weights)
        fair_value = sum(v * w / total_w for v, w in zip(values, weights))

    # Сценарии
    bear = (fair_value * 0.75) if fair_value else None
    base = fair_value
    bull = (fair_value * 1.30) if fair_value else None

    # Апсайд
    price = data.get("price")
    upside = None
    if base and price and price > 0:
        upside = ((base - price) / price) * 100

    return {
        "cca": cca,
        "dcf": dcf,
        "nav": nav,
        "fair_value": fair_value,
        "bear": bear,
        "base": base,
        "bull": bull,
        "upside": upside,
    }


# ─────────────────────────────────────────────
# МОДУЛЬ 4: ГЕНЕРАЦИЯ СИГНАЛА
# ─────────────────────────────────────────────

def generate_signal(data: dict, score: dict, fv: dict) -> dict:
    """Формирует торговый сигнал и предупреждения."""
    print("⚡ Формирую сигнал...")

    upside = fv.get("upside")
    total = score.get("total", 0)
    warnings = []

    # Основной сигнал
    if upside is None:
        signal = "👀 НАБЛЮДАТЬ — недостаточно данных для оценки"
    elif upside > 25 and total >= 5000:
        signal = "📈 СИЛЬНЫЙ ЛОНГ — значительная недооценка"
    elif upside > 10 and total >= 3500:
        signal = "📈 ПОТЕНЦИАЛЬНЫЙ ЛОНГ — умеренная недооценка"
    elif -10 <= upside <= 10:
        signal = "⚖️ ДЕРЖАТЬ — цена около Fair Value"
    elif upside < -25 and total < 2000:
        signal = "📉 СИЛЬНЫЙ ШОРТ — значительная переоценка"
    elif upside < -10 and total < 3500:
        signal = "📉 ПОТЕНЦИАЛЬНЫЙ ШОРТ — переоценка + слабые метрики"
    else:
        signal = "👀 НАБЛЮДАТЬ — смешанные сигналы"

    # Дополнительные предупреждения
    short_pct = data.get("short_pct")
    if short_pct and short_pct * 100 > 10:
        warnings.append("⚠️ Высокий Short Interest — осторожно с лонгом")

    price = data.get("price")
    low52 = data.get("week52_low")
    high52 = data.get("week52_high")
    if price and low52 and price < low52 * 1.05:
        warnings.append("📍 Вблизи 52-недельного минимума")
    if price and high52 and price > high52 * 0.95:
        warnings.append("📍 Вблизи 52-недельного максимума")

    return {"signal": signal, "warnings": warnings}


# ─────────────────────────────────────────────
# МОДУЛЬ 5: НОВОСТИ
# ─────────────────────────────────────────────

def get_news(ticker: str) -> list:
    """Получает последние новости по тикеру через RSS."""
    print("📰 Загружаю новости...")

    if requests is None:
        return []

    urls = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
        "https://feeds.reuters.com/reuters/businessNews",
    ]

    for url in urls:
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            # Пространство имён может отличаться
            ns = {"media": "http://search.yahoo.com/mrss/"}
            items = root.findall(".//item")

            news = []
            for item in items[:10]:
                title_el = item.find("title")
                date_el = item.find("pubDate")
                link_el = item.find("link")

                title = title_el.text if title_el is not None else ""
                date = date_el.text if date_el is not None else ""
                link = link_el.text if link_el is not None else ""

                # Для Reuters фильтруем по тикеру
                if "reuters" in url.lower():
                    if ticker.upper() not in title.upper():
                        continue

                if title:
                    news.append({"title": title, "date": date, "link": link})

                if len(news) >= 5:
                    break

            if news:
                return news

        except Exception:
            continue

    return []


# ─────────────────────────────────────────────
# МОДУЛЬ 6: ГЕНЕРАЦИЯ ОТЧЁТА
# ─────────────────────────────────────────────

def fmt(val, suffix="", decimals=2, pct=False):
    """Форматирует число для вывода."""
    if val is None:
        return "N/A"
    if pct:
        return f"{val * 100:.{decimals}f}%"
    return f"{val:.{decimals}f}{suffix}"


def fmt_large(val):
    """Форматирует большие числа (млрд/млн)."""
    if val is None:
        return "N/A"
    if abs(val) >= 1e12:
        return f"${val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.2f}M"
    return f"${val:.2f}"


def generate_report(data: dict, score: dict, fv: dict, signal_data: dict, news: list):
    """Печатает полный инвестиционный отчёт."""

    ticker = data["ticker"]
    price = data.get("price")
    low52 = data.get("week52_low")
    high52 = data.get("week52_high")
    date_str = datetime.now().strftime("%d.%m.%Y")

    # ── СЕКЦИЯ 1: ЗАГОЛОВОК ──
    print("\n" + "=" * 60)
    print(f"  🔍 ИНВЕСТИЦИОННЫЙ АНАЛИЗ: {ticker}")
    print(f"  {data['name']}")
    print(f"  Сектор: {data['sector']} | Отрасль: {data['industry']}")
    print(f"  Дата: {date_str}")
    print("=" * 60)

    # ── СЕКЦИЯ 2: ЦЕНА И 52-НЕДЕЛЬНЫЙ ДИАПАЗОН ──
    print("\n💰 ТЕКУЩАЯ ЦЕНА")
    print(f"  Цена:              ${fmt(price)}")

    if low52 and high52:
        rng = f"${fmt(low52)} — ${fmt(high52)}"
        print(f"  52-нед. диапазон:  {rng}")
        if price and high52 > low52:
            pos = ((price - low52) / (high52 - low52)) * 100
            print(f"  Позиция:           {pos:.0f}% от диапазона")
    else:
        print("  52-нед. диапазон:  N/A")

    if data.get("market_cap"):
        print(f"  Рын. капитализация:{fmt_large(data['market_cap'])}")
    if data.get("beta"):
        print(f"  Бета:              {fmt(data['beta'])}")

    # ── СЕКЦИЯ 3: МУЛЬТИПЛИКАТОРЫ ──
    print("\n📊 МУЛЬТИПЛИКАТОРЫ")
    header = f"  {'Метрика':<16} {'Значение':>10}  {'Балл':>6}  {'Оценка'}"
    print(header)
    print("  " + "-" * 54)

    metrics = [
        ("P/E", data.get("pe"), "x", score["pe"]),
        ("P/S", data.get("ps"), "x", score["ps"]),
        ("EV/EBITDA", data.get("ev_ebitda"), "x", score["ev_ebitda"]),
        ("P/B", data.get("pb"), "x", (0, "—")),
        ("ROE", data.get("roe"), "%", score["roe"]),
        ("ROA", data.get("roa"), "%", score["roa"]),
        ("D/E", data.get("de"), "x", score["de"]),
        ("Маржа", data.get("margin"), "%", score["margin"]),
    ]

    for name, val, suffix, sc in metrics:
        if val is None:
            val_str = "N/A"
        elif suffix == "%":
            val_str = f"{val*100:.1f}%"
        else:
            val_str = f"{val:.2f}x"
        pts = sc[0] if sc[0] != 0 else "—"
        comment = sc[1]
        print(f"  {name:<16} {val_str:>10}  {str(pts):>6}  {comment}")

    # ── СЕКЦИЯ 4: СКОРИНГ ──
    print("\n🎯 СКОРИНГОВЫЙ БАЛЛ")
    breakdown = [
        ("P/E", score["pe"][0]),
        ("P/S", score["ps"][0]),
        ("EV/EBITDA", score["ev_ebitda"][0]),
        ("ROE", score["roe"][0]),
        ("ROA", score["roa"][0]),
        ("D/E", score["de"][0]),
        ("Маржа", score["margin"][0]),
        ("Short Interest", score["short"][0]),
    ]

    for label, pts in breakdown:
        sign = "+" if pts >= 0 else ""
        print(f"  {label:<20} {sign}{pts}")
    print("  " + "─" * 28)
    print(f"  {'ИТОГО:':<20} {score['total']} баллов")
    print(f"  РЕЙТИНГ:             {score['rating']}")

    # ── СЕКЦИЯ 5: FAIR VALUE ──
    print("\n💰 FAIR VALUE")
    print(f"  CCA (консенсус):    ${fmt(fv.get('cca'))}")
    print(f"  DCF (упрощённый):   ${fmt(fv.get('dcf'))}")
    print(f"  NAV (EV метод):     ${fmt(fv.get('nav'))}")
    print("  " + "─" * 30)
    print(f"  Fair Value (Base):  ${fmt(fv.get('fair_value'))}")
    print()

    bear = fv.get("bear")
    base = fv.get("base")
    bull = fv.get("bull")
    upside = fv.get("upside")

    print(f"  🐻 Bear сценарий:   ${fmt(bear)}")
    print(f"  ⚖️  Base сценарий:  ${fmt(base)}")
    print(f"  🐂 Bull сценарий:   ${fmt(bull)}")
    print()
    print(f"  Текущая цена:       ${fmt(price)}")

    if upside is not None:
        sign = "+" if upside >= 0 else ""
        print(f"  Апсайд до Base:     {sign}{upside:.1f}%")
    else:
        print("  Апсайд до Base:     N/A")

    # ── СЕКЦИЯ 6: СИГНАЛЫ РИСКА ──
    print("\n⚡ СИГНАЛЫ РИСКА")
    short_pct = data.get("short_pct")
    if short_pct is not None:
        si_comment = score["short"][1]
        print(f"  Short Interest:  {short_pct*100:.1f}%  {si_comment}")
    else:
        print("  Short Interest:  N/A")

    if low52 and high52 and price:
        pos = ((price - low52) / (high52 - low52)) * 100
        pos_note = ""
        if price > high52 * 0.95:
            pos_note = "  📍 Вблизи 52-нед. максимума"
        elif price < low52 * 1.05:
            pos_note = "  📍 Вблизи 52-нед. минимума"
        print(f"  52-нед. позиция: {pos:.0f}%{pos_note}")

    for w in signal_data.get("warnings", []):
        print(f"  {w}")

    # ── СЕКЦИЯ 7: НОВОСТИ ──
    print("\n📰 ПОСЛЕДНИЕ НОВОСТИ")
    if news:
        for item in news[:5]:
            # Обрезаем дату до читаемого вида
            raw_date = item.get("date", "")
            short_date = raw_date[:16] if raw_date else "—"
            title = item.get("title", "")[:80]
            print(f"  [{short_date}] {title}")
    else:
        print("  Новости временно недоступны")

    # ── СЕКЦИЯ 8: ЧЕКЛИСТ ──
    print("\n✅ ЧЕКЛИСТ")
    total_score = score["total"]
    upside_val = fv.get("upside")
    short_val = data.get("short_pct")
    de_val = data.get("de")
    roe_val = data.get("roe")

    def chk(cond):
        return "✅" if cond else "❌"

    print(f"  {chk(total_score >= 5000)} Скоринг > 5000 баллов ({total_score})")

    if upside_val is not None:
        print(f"  {chk(upside_val > 15)} Апсайд > 15% ({upside_val:.1f}%)")
    else:
        print("  ❌ Апсайд > 15% (N/A)")

    if short_val is not None:
        print(f"  {chk(short_val * 100 < 5)} Short Interest < 5% ({short_val*100:.1f}%)")
    else:
        print("  ❌ Short Interest < 5% (N/A)")

    if de_val is not None:
        print(f"  {chk(de_val < 3)} D/E < 3x ({de_val:.2f}x)")
    else:
        print("  ❌ D/E < 3x (N/A)")

    if roe_val is not None:
        print(f"  {chk(roe_val * 100 > 10)} ROE > 10% ({roe_val*100:.1f}%)")
    else:
        print("  ❌ ROE > 10% (N/A)")

    if price and high52:
        pct_below_high = ((high52 - price) / high52) * 100
        print(f"  {chk(pct_below_high > 10)} Цена ниже 52-нед. максимума на 10%+ ({pct_below_high:.0f}% ниже пика)")
    else:
        print("  ❌ Цена ниже 52-нед. максимума на 10%+ (N/A)")

    # ── СЕКЦИЯ 9: ИТОГОВЫЙ СИГНАЛ ──
    print("\n" + "=" * 60)
    print(f"  ИТОГОВЫЙ СИГНАЛ: {signal_data['signal']}")
    print()
    print("  Disclaimer: Это аналитический инструмент,")
    print("  не инвестиционный совет.")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────
# ТОЧКА ВХОДА
# ─────────────────────────────────────────────

def main():
    """Главная функция: разбор аргументов и запуск анализа."""
    parser = argparse.ArgumentParser(
        description="Инвестиционный агент анализа акций",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Пример: python agent.py --ticker LMT"
    )
    parser.add_argument(
        "--ticker",
        required=True,
        type=str,
        help="Тикер акции (например: AAPL, LMT, MSFT, BTC-USD)"
    )
    args = parser.parse_args()
    ticker = args.ticker.strip().upper()

    # Последовательный запуск всех модулей
    data = get_data(ticker)
    score = calculate_score(data)
    fv = calculate_fair_value(data)
    signal_data = generate_signal(data, score, fv)
    news = get_news(ticker)

    generate_report(data, score, fv, signal_data, news)


if __name__ == "__main__":
    main()
