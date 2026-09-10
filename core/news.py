# -*- coding: utf-8 -*-
# Новости через RSS. Кэш в SQLite (5 мин).
import xml.etree.ElementTree as ET
from .db import get_news_cache, save_news, init_db

try:
    import requests as _req
except ImportError:
    _req = None

def _fetch_rss(ticker: str) -> list:
    if _req is None:
        return []
    urls = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    ]
    for url in urls:
        try:
            r = _req.get(url, timeout=8)
            if r.status_code != 200:
                continue
            root  = ET.fromstring(r.content)
            items = root.findall(".//item")
            news  = []
            for it in items[:10]:
                title = (it.find("title") or type("", (), {"text": ""})()).text or ""
                date  = (it.find("pubDate") or type("", (), {"text": ""})()).text or ""
                link  = (it.find("link") or type("", (), {"text": ""})()).text or ""
                if title:
                    news.append({"title": title, "date": date, "link": link})
                if len(news) >= 5:
                    break
            if news:
                return news
        except Exception:
            continue
    return []

def get_news(ticker: str, use_cache: bool = True) -> list:
    init_db()
    ticker = ticker.upper()
    if use_cache:
        cached = get_news_cache(ticker)
        if cached:
            return cached
    news = _fetch_rss(ticker)
    if news:
        save_news(ticker, news)
    return news
