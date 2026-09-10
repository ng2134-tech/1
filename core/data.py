# -*- coding: utf-8 -*-
# Сбор данных с кэшем (SQLite) и fallback через реестр.
import sys
from .db import cache_get, cache_set, init_db
from .registry import REGISTRY, Source

try:
    import yfinance as yf
except ImportError:
    yf = None

# ── регистрируем yfinance как основной источник ──────────────────
def _yf_fetch(ticker: str) -> dict:
    if yf is None:
        raise RuntimeError("yfinance не установлен")
    stock = yf.Ticker(ticker)
    info  = stock.info
    name  = info.get("longName") or info.get("shortName")
    if not name:
        raise ValueError(f"Тикер '{ticker}' не найден")
    price      = info.get("currentPrice") or info.get("regularMarketPrice")
    market_cap = info.get("marketCap")
    shares     = (market_cap / price) if (market_cap and price) else None
    raw_de     = info.get("debtToEquity")
    return {
        "ticker": ticker.upper(), "name": name,
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "price": price, "market_cap": market_cap,
        "beta": info.get("beta"),
        "pe": info.get("trailingPE"),
        "ps": info.get("priceToSalesTrailing12Months"),
        "pb": info.get("priceToBook"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ev_sales": info.get("enterpriseToRevenue"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "de": (raw_de / 100) if raw_de is not None else None,
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

REGISTRY.register("fundamentals", Source(
    name="yfinance", priority=1, fetch=_yf_fetch, rate_limit=30
))

def get_data(ticker: str, use_cache: bool = True, ttl: float = 900) -> dict:
    """Возвращает данные по тикеру. Кэш — 15 минут по умолчанию."""
    init_db()
    ticker = ticker.upper()
    if use_cache:
        cached = cache_get(ticker, "fundamentals", ttl)
        if cached:
            return cached
    try:
        data = REGISTRY.fetch("fundamentals", ticker=ticker)
        cache_set(ticker, "fundamentals", data)
        return data
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("proxy", "tunnel", "403", "curl", "ssl", "certificate")):
            raise ConnectionError(
                "Нет доступа к интернету — прокси или SSL блокирует запрос"
            ) from e
        if "429" in err or "rate limit" in err:
            raise ConnectionError(
                "Слишком много запросов к yfinance (429). Подождите пару минут."
            ) from e
        if "не найден" in str(e):
            raise ValueError(str(e)) from e
        raise

def get_history(ticker: str, period: str = "6mo", interval: str = "1d"):
    """Возвращает DataFrame с историческими ценами для TA."""
    if yf is None:
        return None
    try:
        return yf.Ticker(ticker.upper()).history(period=period, interval=interval)
    except Exception:
        return None
