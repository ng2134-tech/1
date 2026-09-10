# -*- coding: utf-8 -*-
# Генерация полного отчёта в консоль (9 секций).
from datetime import datetime

def fmt(val, decimals=2):
    return "N/A" if val is None else f"{val:.{decimals}f}"

def fmt_large(val):
    if val is None: return "N/A"
    a = abs(val)
    if a >= 1e12: return f"${val/1e12:.2f}T"
    if a >= 1e9:  return f"${val/1e9:.2f}B"
    if a >= 1e6:  return f"${val/1e6:.2f}M"
    return f"${val:.2f}"

def generate_report(data, score, fv, sig, news, tech=None):
    t      = data["ticker"]
    price  = data.get("price")
    low52  = data.get("week52_low")
    high52 = data.get("week52_high")

    print("\n" + "=" * 62)
    print(f"  \U0001f50d ИНВЕСТИЦИОННЫЙ АНАЛИЗ: {t}")
    print(f"  {data['name']}")
    print(f"  Сектор: {data['sector']} | Отрасль: {data['industry']}")
    print(f"  Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 62)

    print("\n\U0001f4b0 ТЕКУЩАЯ ЦЕНА")
    print(f"  Цена:               ${fmt(price)}")
    if low52 and high52:
        print(f"  52-нед. диапазон:   ${fmt(low52)} — ${fmt(high52)}")
        if price and high52 > low52:
            print(f"  Позиция:            {((price-low52)/(high52-low52)*100):.0f}% от диапазона")
    if data.get("market_cap"):
        print(f"  Капитализация:      {fmt_large(data['market_cap'])}")
    if data.get("beta"):
        print(f"  Бета:               {fmt(data['beta'])}")

    print("\n\U0001f4ca МУЛЬТИПЛИКАТОРЫ")
    print(f"  {'Метрика':<14}{'Значение':>11}  {'Балл':>6}  Оценка")
    print("  " + "─" * 56)
    rows = [
        ("P/E",       data.get("pe"),        "x", score["pe"]),
        ("P/S",       data.get("ps"),        "x", score["ps"]),
        ("EV/EBITDA", data.get("ev_ebitda"), "x", score["ev_ebitda"]),
        ("P/B",       data.get("pb"),        "x", (0, "—")),
        ("ROE",       data.get("roe"),       "%", score["roe"]),
        ("ROA",       data.get("roa"),       "%", score["roa"]),
        ("D/E",       data.get("de"),        "x", score["de"]),
        ("Маржа",     data.get("margin"),    "%", score["margin"]),
    ]
    for name, val, suf, sc in rows:
        v = "N/A" if val is None else (f"{val*100:.1f}%" if suf == "%" else f"{val:.2f}x")
        pts = sc[0] if sc[0] != 0 else "—"
        print(f"  {name:<14}{v:>11}  {str(pts):>6}  {sc[1]}")

    if tech and tech.get("available"):
        print("\n\U0001f4c8 ТЕХНИЧЕСКИЙ АНАЛИЗ")
        print(f"  RSI (14):           {tech['rsi']}  {tech['rsi_comment']}")
        print(f"  MACD:               {tech['macd']}  {tech['macd_trend']}")
        print(f"  Bollinger:          {tech['bb_low']} / {tech['bb_mid']} / {tech['bb_high']}")
        print(f"  Позиция:            {tech['bb_comment']}")

    print("\n\U0001f3af СКОРИНГОВЫЙ БАЛЛ")
    for lbl, k in [("P/E","pe"),("P/S","ps"),("EV/EBITDA","ev_ebitda"),("ROE","roe"),
                   ("ROA","roa"),("D/E","de"),("Маржа","margin"),("Short Interest","short")]:
        p = score[k][0]
        print(f"  {lbl:<20}{'+' if p >= 0 else ''}{p}")
    print("  " + "─" * 28)
    print(f"  {'ИТОГО:':<20}{score['total']} баллов")
    print(f"  РЕЙТИНГ:            {score['rating']}")

    print("\n\U0001f4b0 FAIR VALUE")
    print(f"  CCA (консенсус):    ${fmt(fv.get('cca'))}")
    print(f"  DCF (упрощённый):   ${fmt(fv.get('dcf'))}")
    print(f"  NAV (EV метод):     ${fmt(fv.get('nav'))}")
    print("  " + "─" * 30)
    print(f"  Fair Value (Base):  ${fmt(fv.get('fair_value'))}\n")
    print(f"  \U0001f43b Bear:            ${fmt(fv.get('bear'))}")
    print(f"  ⚖️  Base:            ${fmt(fv.get('base'))}")
    print(f"  \U0001f42e Bull:            ${fmt(fv.get('bull'))}\n")
    print(f"  Текущая цена:       ${fmt(price)}")
    up = fv.get("upside")
    print(f"  Апсайд до Base:     {'+' if up and up >= 0 else ''}{fmt(up,1) if up is not None else 'N/A'}%")

    print("\n⚡ СИГНАЛЫ РИСКА")
    sp = data.get("short_pct")
    if sp is not None:
        print(f"  Short Interest:     {sp*100:.1f}%  {score['short'][1]}")
    else:
        print("  Short Interest:     N/A")
    if low52 and high52 and price:
        pos  = (price - low52) / (high52 - low52) * 100
        note = ""
        if price > high52 * 0.95:  note = "  \U0001f4cd Вблизи максимума"
        elif price < low52 * 1.05: note = "  \U0001f4cd Вблизи минимума"
        print(f"  52-нед. позиция:    {pos:.0f}%{note}")
    for w in sig.get("warnings", []):
        print(f"  {w}")

    print("\n\U0001f4f0 ПОСЛЕДНИЕ НОВОСТИ")
    if news:
        for it in news[:5]:
            d = (it.get("date") or "")[:16] or "—"
            print(f"  [{d}] {it.get('title','')[:75]}")
    else:
        print("  Новости временно недоступны")

    print("\n✅ ЧЕКЛИСТ")
    chk = lambda c: "✅" if c else "❌"
    ts, de_v, roe_v = score["total"], data.get("de"), data.get("roe")
    print(f"  {chk(ts >= 5000)} Скоринг > 5000 баллов ({ts})")
    print(f"  {chk(up is not None and up > 15)} Апсайд > 15% ({fmt(up,1) if up is not None else 'N/A'}%)")
    print(f"  {chk(sp is not None and sp*100 < 5)} Short Interest < 5% ({f'{sp*100:.1f}%' if sp is not None else 'N/A'})")
    print(f"  {chk(de_v is not None and de_v < 3)} D/E < 3x ({fmt(de_v) if de_v is not None else 'N/A'}x)")
    print(f"  {chk(roe_v is not None and roe_v*100 > 10)} ROE > 10% ({f'{roe_v*100:.1f}%' if roe_v is not None else 'N/A'})")
    if price and high52:
        below = (high52 - price) / high52 * 100
        print(f"  {chk(below > 10)} Цена ниже 52-нед. максимума на 10%+ ({below:.0f}% ниже)")

    print("\n" + "=" * 62)
    print(f"  ИТОГОВЫЙ СИГНАЛ: {sig['signal']}")
    print("\n  Disclaimer: аналитический инструмент, не инвестиционный совет.")
    print("=" * 62 + "\n")
