#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инвестиционный терминал — веб-версия.

Запуск: python web.py  (или двойной клик по файлу)
Откроется в браузере на http://127.0.0.1:8765

Только стандартная библиотека — ничего доустанавливать не нужно.
"""
import json, sys, threading, webbrowser, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

PORT = 8765
HTML = None   # читается в main()

# Импорты держим в функции: при запуске двойным кликом ошибка на уровне
# модуля закрыла бы окно раньше, чем её успели прочитать.
def _load():
    global get_data, get_history, calculate_score, calculate_fair_value
    global generate_signal, calculate_technical, get_news
    global init_db, save_signal, REGISTRY, T, HTML

    here = Path(__file__).parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    from core.data       import get_data, get_history
    from core.scoring    import calculate_score
    from core.fair_value import calculate_fair_value
    from core.signals    import generate_signal
    from core.technical  import calculate_technical
    from core.news       import get_news
    from core.db         import init_db, save_signal
    from core.registry   import REGISTRY
    import terminal as T          # переиспользуем вотчлист и analyze()

    ui = here / "ui.html"
    if not ui.exists():
        raise FileNotFoundError(
            f"Рядом с web.py нет файла ui.html (ожидался тут: {ui}).\n"
            "Скачайте проект целиком — web.py и ui.html должны лежать в одной папке."
        )
    HTML = ui.read_text(encoding="utf-8")


def full_payload(ticker: str) -> dict:
    """Полный анализ одного тикера в виде JSON-совместимого словаря."""
    try:
        data  = get_data(ticker)
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)[:200]}

    score = calculate_score(data)
    fv    = calculate_fair_value(data)
    sig   = generate_signal(data, score, fv)
    tech  = calculate_technical(get_history(ticker))
    news  = get_news(ticker)
    save_signal(ticker, score["total"], sig["signal"], fv.get("upside"), data.get("price"))

    price, hi, lo = data.get("price"), data.get("week52_high"), data.get("week52_low")
    pos = ((price - lo) / (hi - lo) * 100) if (price and hi and lo and hi > lo) else None

    return {
        "ticker": ticker, "ok": True,
        "name": data.get("name"), "sector": data.get("sector"),
        "industry": data.get("industry"),
        "price": price, "week52_high": hi, "week52_low": lo, "range_pos": pos,
        "market_cap": data.get("market_cap"), "beta": data.get("beta"),
        "metrics": [
            {"name": "P/E",       "value": data.get("pe"),        "unit": "x",
             "points": score["pe"][0],        "comment": score["pe"][1]},
            {"name": "P/S",       "value": data.get("ps"),        "unit": "x",
             "points": score["ps"][0],        "comment": score["ps"][1]},
            {"name": "EV/EBITDA", "value": data.get("ev_ebitda"), "unit": "x",
             "points": score["ev_ebitda"][0], "comment": score["ev_ebitda"][1]},
            {"name": "ROE",       "value": data.get("roe"),       "unit": "%",
             "points": score["roe"][0],       "comment": score["roe"][1]},
            {"name": "ROA",       "value": data.get("roa"),       "unit": "%",
             "points": score["roa"][0],       "comment": score["roa"][1]},
            {"name": "D/E",       "value": data.get("de"),        "unit": "x",
             "points": score["de"][0],        "comment": score["de"][1]},
            {"name": "Маржа",     "value": data.get("margin"),    "unit": "%",
             "points": score["margin"][0],    "comment": score["margin"][1]},
            {"name": "Short Int.","value": data.get("short_pct"), "unit": "%",
             "points": score["short"][0],     "comment": score["short"][1]},
        ],
        "score": score["total"], "rating": score["rating"],
        "fv": fv, "signal": sig["signal"], "warnings": sig["warnings"],
        "tech": tech, "news": news,
        # na=True — значение неизвестно. Без этого пункт рисуется красным
        # крестом, то есть «проверка провалена», хотя данных просто нет.
        "checklist": [
            {"na": score["scored"] < 4, "ok": score["total"] >= 5000,
             "label": "Скоринг > 5000 баллов", "actual": f"{score['total']}"},
            {"na": fv.get("upside") is None, "ok": fv.get("upside") is not None and fv["upside"] > 15,
             "label": "Апсайд > 15%",
             "actual": (f"{fv['upside']:.1f}%" if fv.get("upside") is not None else "нет данных")},
            {"na": data.get("short_pct") is None,
             "ok": data.get("short_pct") is not None and data["short_pct"]*100 < 5,
             "label": "Short Interest < 5%",
             "actual": (f"{data['short_pct']*100:.1f}%" if data.get("short_pct") is not None else "нет данных")},
            {"na": data.get("de") is None, "ok": data.get("de") is not None and data["de"] < 3,
             "label": "D/E < 3x",
             "actual": (f"{data['de']:.2f}x" if data.get("de") is not None else "нет данных")},
            {"na": data.get("roe") is None, "ok": data.get("roe") is not None and data["roe"]*100 > 10,
             "label": "ROE > 10%",
             "actual": (f"{data['roe']*100:.1f}%" if data.get("roe") is not None else "нет данных")},
            {"na": not (price and hi),
             "ok": (price is not None and hi is not None and (hi-price)/hi*100 > 10),
             "label": "Цена ниже 52-нед. максимума на 10%+",
             "actual": (f"{(hi-price)/hi*100:.0f}%" if (price and hi) else "нет данных")},
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # не засоряем консоль

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path == "/":
            return self._send(200, HTML, "text/html; charset=utf-8")

        if u.path == "/api/watchlist":
            wl = T.load_watchlist()
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as ex:
                rows = list(ex.map(T.analyze, wl))
            return self._send(200, json.dumps({
                "rows": rows,
                "sources": REGISTRY.status(),
                "updated": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            }, ensure_ascii=False))

        if u.path == "/api/ticker":
            t = (q.get("t", [""])[0] or "").strip().upper()
            if not t:
                return self._send(400, json.dumps({"error": "не указан тикер"}, ensure_ascii=False))
            return self._send(200, json.dumps(full_payload(t), ensure_ascii=False))

        if u.path in ("/api/add", "/api/remove"):
            t = (q.get("t", [""])[0] or "").strip().upper()
            wl = T.load_watchlist()
            if u.path == "/api/add" and t and t not in wl:
                wl.append(t)
            elif u.path == "/api/remove" and t in wl:
                wl.remove(t)
            T.save_watchlist(wl)
            return self._send(200, json.dumps({"watchlist": wl}, ensure_ascii=False))

        self._send(404, json.dumps({"error": "not found"}))


def main():
    _load()
    init_db()
    global PORT
    srv = None
    for port in range(PORT, PORT + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            PORT = port
            break
        except OSError:
            continue
    if srv is None:
        print("❌ Не удалось занять порт. Закройте другие копии терминала.")
        return

    url = f"http://127.0.0.1:{PORT}"
    print("=" * 58)
    print("  ИНВЕСТИЦИОННЫЙ ТЕРМИНАЛ")
    print(f"  Открыт в браузере: {url}")
    print("  Закрыть: Ctrl+C в этом окне")
    print("=" * 58)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")


if __name__ == "__main__":
    # При запуске двойным кликом окно закрывается мгновенно и ошибку не видно,
    # поэтому держим его открытым до нажатия Enter.
    try:
        main()
    except Exception:
        traceback.print_exc()
        try:
            input("\nПроизошла ошибка. Нажмите Enter чтобы закрыть...")
        except EOFError:
            pass
