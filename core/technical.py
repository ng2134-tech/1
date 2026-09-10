# -*- coding: utf-8 -*-
# Технический анализ: RSI, MACD, Bollinger Bands.
# Вычисляется по историческим данным из yfinance.

def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_g  = sum(gains[:period]) / period
    avg_l  = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * 13 + gains[i]) / 14
        avg_l = (avg_l * 13 + losses[i]) / 14
    if avg_l == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_g / avg_l), 1)

def _ema(values, period):
    if len(values) < period:
        return []
    k   = 2 / (period + 1)
    ema = [sum(values[:period]) / period]
    for v in values[period:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema

def _macd(closes):
    if len(closes) < 26:
        return None, None, None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    offset = len(ema12) - len(ema26)
    macd_line   = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
    signal_line = _ema(macd_line, 9)
    if not signal_line:
        return None, None, None
    return round(macd_line[-1], 4), round(signal_line[-1], 4), round(macd_line[-1] - signal_line[-1], 4)

def _bollinger(closes, period=20):
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    mid  = sum(window) / period
    std  = (sum((x - mid)**2 for x in window) / period) ** 0.5
    return round(mid - 2*std, 2), round(mid, 2), round(mid + 2*std, 2)

def calculate_technical(history) -> dict:
    """Принимает DataFrame от yfinance, возвращает словарь с TA."""
    if history is None or len(history) < 20:
        return {"available": False}
    closes = list(history["Close"].values.tolist())

    rsi  = _rsi(closes)
    macd, macd_signal, macd_hist = _macd(closes)
    bb_low, bb_mid, bb_high = _bollinger(closes)
    price = closes[-1]

    # Интерпретация RSI
    if rsi is None:
        rsi_comment = "N/A"
    elif rsi > 70:
        rsi_comment = "Перекуплен ⚠️"
    elif rsi < 30:
        rsi_comment = "Перепродан ✅"
    else:
        rsi_comment = "Нейтральный"

    # Тренд по MACD
    macd_trend = "N/A"
    if macd is not None and macd_signal is not None:
        macd_trend = "↑ Бычий" if macd > macd_signal else "↓ Медвежий"

    # Позиция в Bollinger
    bb_comment = "N/A"
    if bb_low and bb_high and price:
        if price > bb_high:
            bb_comment = "Выше верхней полосы ⚠️"
        elif price < bb_low:
            bb_comment = "Ниже нижней полосы ✅"
        else:
            bb_comment = "Внутри полос"

    return {
        "available": True,
        "rsi": rsi, "rsi_comment": rsi_comment,
        "macd": macd, "macd_signal": macd_signal,
        "macd_hist": macd_hist, "macd_trend": macd_trend,
        "bb_low": bb_low, "bb_mid": bb_mid, "bb_high": bb_high,
        "bb_comment": bb_comment,
    }
