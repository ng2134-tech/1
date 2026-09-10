# -*- coding: utf-8 -*-
# Генерация торгового сигнала на основе скоринга и апсайда.

def generate_signal(data: dict, score: dict, fv: dict) -> dict:
    upside = fv.get("upside")
    total  = score.get("total", 0)
    warnings = []

    if upside is None:
        signal = "👀 НАБЛЮДАТЬ — недостаточно данных"
    elif upside > 25 and total >= 5000:
        signal = "📈 СИЛЬНЫЙ ЛОНГ — значительная недооценка"
    elif upside > 10 and total >= 3500:
        signal = "📈 ПОТЕНЦИАЛЬНЫЙ ЛОНГ — умеренная недооценка"
    elif -10 <= upside <= 10:
        signal = "⚖️ ДЕРЖАТЬ — цена около Fair Value"
    elif upside < -25 and total < 2000:
        signal = "📉 СИЛЬНЫЙ ШОРТ — значительная переоценка"
    elif upside < -10 and total < 3500:
        signal = "📉 ПОТЕНЦ. ШОРТ — переоценка + слабые метрики"
    else:
        signal = "👀 НАБЛЮДАТЬ — смешанные сигналы"

    price  = data.get("price")
    low52  = data.get("week52_low")
    high52 = data.get("week52_high")
    short  = data.get("short_pct")

    if short and short * 100 > 10:
        warnings.append("⚠️ Высокий Short Interest — осторожно с лонгом")
    if price and low52 and price < low52 * 1.05:
        warnings.append("📍 Вблизи 52-нед. минимума")
    if price and high52 and price > high52 * 0.95:
        warnings.append("📍 Вблизи 52-нед. максимума")

    return {"signal": signal, "warnings": warnings}
