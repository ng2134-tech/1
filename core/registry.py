# -*- coding: utf-8 -*-
# Реестр источников данных с fallback и rate-limit.
# Паттерн: capability registry из архитектуры TR.
import time
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class Source:
    name: str
    priority: int           # меньше = выше приоритет
    fetch: Callable
    rate_limit: float = 15  # минимум секунд между вызовами
    _last: float = field(default=0.0, repr=False)
    _fails: int = field(default=0, repr=False)

    def available(self) -> bool:
        if self._fails >= 5:
            return False
        if time.time() - self._last < self.rate_limit:
            return False
        return True

    def call(self, **kw) -> Any:
        self._last = time.time()
        try:
            result = self.fetch(**kw)
            self._fails = 0
            return result
        except Exception as e:
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
