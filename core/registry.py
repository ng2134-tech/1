# -*- coding: utf-8 -*-
# Реестр источников данных с fallback и rate-limit.
# Паттерн: capability registry из архитектуры TR.
import time, threading
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class Source:
    name: str
    priority: int           # меньше = выше приоритет
    fetch: Callable
    rate_limit: float = 0.5 # минимальный интервал между вызовами, секунд
    _last: float = field(default=0.0, repr=False)
    _fails: int = field(default=0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def available(self) -> bool:
        # Только счётчик сбоев. Интервал между запросами источник не делает
        # недоступным — иначе запрос по второму тикеру считался бы сбоем.
        return self._fails < 5

    def call(self, **kw) -> Any:
        # Разносим вызовы во времени, а не пропускаем их: под замком ждём
        # свой слот, сам запрос выполняем уже параллельно.
        with self._lock:
            wait = self.rate_limit - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
        try:
            result = self.fetch(**kw)
            self._fails = 0
            return result
        except Exception:
            self._fails += 1
            raise

class Registry:
    def __init__(self):
        self._sources: dict[str, list[Source]] = {}

    def register(self, topic: str, source: Source):
        self._sources.setdefault(topic, []).append(source)
        self._sources[topic].sort(key=lambda s: s.priority)

    def fetch(self, topic: str, **kw) -> Any:
        last_error = None
        for src in self._sources.get(topic, []):
            if not src.available():
                continue
            try:
                return src.call(**kw)
            except Exception as e:
                last_error = e
                continue
        # Пробрасываем последнюю ошибку — иначе теряется причина
        # (прокси / 429 / тикер не найден), а она нужна вызывающему коду.
        raise RuntimeError(
            f"Все источники недоступны для '{topic}'"
            + (f": {last_error}" if last_error else "")
        ) from last_error

    def status(self) -> dict:
        out = {}
        for topic, sources in self._sources.items():
            out[topic] = [
                {"name": s.name, "fails": s._fails, "ok": s.available()}
                for s in sources
            ]
        return out

# Глобальный реестр
REGISTRY = Registry()
