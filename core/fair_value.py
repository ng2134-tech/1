# -*- coding: utf-8 -*-
# Расчёт справедливой стоимости: CCA 40% + DCF 40% + NAV 20%.

def calculate_fair_value(data: dict) -> dict:
    cca = data.get("target_price")
    if not cca:
        fwd = data.get("eps_forward")
        if fwd and fwd > 0:
            cca = fwd * 18

    dcf = None
    if data.get("eps_forward") and data["eps_forward"] > 0:
        dcf = data["eps_forward"] * 20
    elif data.get("eps_trailing") and data["eps_trailing"] > 0:
        dcf = data["eps_trailing"] * 18

    nav = None
    ebitda = data.get("ebitda")
    debt   = data.get("total_debt") or 0
    shares = data.get("shares")
    if ebitda and ebitda > 0 and shares and shares > 0:
        nav = (ebitda * 12 - debt) / shares

    weights, values = [], []
    if cca: weights.append(0.4); values.append(cca)
    if dcf: weights.append(0.4); values.append(dcf)
    if nav: weights.append(0.2); values.append(nav)

    if not values:
        fv = None
    else:
        tw = sum(weights)
        fv = sum(v * w / tw for v, w in zip(values, weights))

    price  = data.get("price")
    upside = ((fv - price) / price * 100) if (fv and price and price > 0) else None

    return {
        "cca": cca, "dcf": dcf, "nav": nav,
        "fair_value": fv,
        "bear": fv * 0.75 if fv else None,
        "base": fv,
        "bull": fv * 1.30 if fv else None,
        "upside": upside,
    }
