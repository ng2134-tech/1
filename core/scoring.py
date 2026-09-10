# -*- coding: utf-8 -*-
# Скоринговая система (0–8000 баллов). Перенесено из agent.py без изменений.

def score_pe(pe):
    if pe is None or pe <= 0: return 0, "N/A"
    if pe < 10:  return 1000, "Очень низкий ✅"
    if pe < 15:  return 900,  "Низкий ✅"
    if pe < 25:  return 750,  "Умеренный ⚠️"
    if pe < 35:  return 500,  "Высокий ⚠️"
    return 300, "Очень высокий ❌"

def score_ps(ps):
    if ps is None: return 0, "N/A"
    if ps < 1: return 1000, "Очень низкий ✅"
    if ps < 2: return 900,  "Низкий ✅"
    if ps < 4: return 700,  "Умеренный ⚠️"
    if ps < 8: return 450,  "Высокий ⚠️"
    return 250, "Очень высокий ❌"

def score_ev_ebitda(ev):
    if ev is None or ev <= 0: return 0, "N/A"
    if ev < 8:  return 1000, "Очень низкий ✅"
    if ev < 12: return 880,  "Низкий ✅"
    if ev < 18: return 700,  "Умеренный ⚠️"
    if ev < 25: return 450,  "Высокий ⚠️"
    return 250, "Очень высокий ❌"

def score_roe(roe):
    if roe is None: return 0, "N/A"
    p = roe * 100
    if p > 30: return 1000, "Высокий ✅"
    if p > 20: return 900,  "Хороший ✅"
    if p > 10: return 700,  "Средний ⚠️"
    if p > 0:  return 400,  "Низкий ⚠️"
    return 100, "Отрицательный ❌"

def score_roa(roa):
    if roa is None: return 0, "N/A"
    p = roa * 100
    if p > 15: return 1000, "Высокий ✅"
    if p > 10: return 850,  "Хороший ✅"
    if p > 5:  return 700,  "Средний ⚠️"
    if p > 0:  return 400,  "Низкий ⚠️"
    return 100, "Отрицательный ❌"

def score_de(de):
    if de is None: return 0, "N/A"
    if de < 0.3: return 1000, "Очень низкий ✅"
    if de < 1:   return 900,  "Низкий ✅"
    if de < 2:   return 750,  "Умеренный ⚠️"
    if de < 3.5: return 500,  "Высокий ⚠️"
    return 200, "Очень высокий ❌"

def score_margin(m):
    if m is None: return 0, "N/A"
    p = m * 100
    if p > 25: return 1000, "Очень высокая ✅"
    if p > 15: return 900,  "Высокая ✅"
    if p > 10: return 750,  "Хорошая ✅"
    if p > 5:  return 550,  "Средняя ⚠️"
    if p > 0:  return 300,  "Низкая ⚠️"
    return 50, "Отрицательная ❌"

def score_short(s):
    if s is None: return 0, "N/A"
    p = s * 100
    if p < 2:  return  200, "Низкий шорт ✅"
    if p < 5:  return  100, "Нормальный"
    if p < 10: return -100, "Повышенный ⚠️"
    return -300, "Высокий шорт ❌"

def get_rating(score, scored=8):
    # Без данных скоринг = 0, но это не «плохо», а «неизвестно»: у крипты и
    # фондов нет P/E и ROE в принципе. Иначе BTC получал бы вердикт
    # «очень слабая оценка» — фактически ложный сигнал.
    if scored < 4:      return "НЕДОСТАТОЧНО ДАННЫХ — методика неприменима"
    if score >= 6500:   return "ОТЛИЧНАЯ ОЦЕНКА ✅✅"
    if score >= 5000:   return "ХОРОШАЯ ОЦЕНКА ✅"
    if score >= 3500:   return "СРЕДНЯЯ ОЦЕНКА ⚠️"
    if score >= 2000:   return "СЛАБАЯ ОЦЕНКА ❌"
    return "ОЧЕНЬ СЛАБАЯ ОЦЕНКА ❌❌"

def calculate_score(data: dict) -> dict:
    pe_s,  pe_c  = score_pe(data.get("pe"))
    ps_s,  ps_c  = score_ps(data.get("ps"))
    ev_s,  ev_c  = score_ev_ebitda(data.get("ev_ebitda"))
    roe_s, roe_c = score_roe(data.get("roe"))
    roa_s, roa_c = score_roa(data.get("roa"))
    de_s,  de_c  = score_de(data.get("de"))
    mg_s,  mg_c  = score_margin(data.get("margin"))
    sh_s,  sh_c  = score_short(data.get("short_pct"))
    total = pe_s + ps_s + ev_s + roe_s + roa_s + de_s + mg_s + sh_s
    # Сколько метрик реально удалось оценить — от этого зависит, можно ли
    # вообще трактовать итоговый балл.
    scored = sum(1 for c in (pe_c, ps_c, ev_c, roe_c, roa_c, de_c, mg_c, sh_c)
                 if c != "N/A")
    return {
        "pe": (pe_s, pe_c), "ps": (ps_s, ps_c),
        "ev_ebitda": (ev_s, ev_c), "roe": (roe_s, roe_c),
        "roa": (roa_s, roa_c), "de": (de_s, de_c),
        "margin": (mg_s, mg_c), "short": (sh_s, sh_c),
        "total": total, "scored": scored, "rating": get_rating(total, scored),
    }
