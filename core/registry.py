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
    max_fails: int = 5      # после стольких неудач подряд источник уходит в паузу
    cooldown: float = 60    # ...на столько секунд, потом пробуем снова
    _last: float = field(default=0.0, repr=False)
    _fails: int = field(default=0, repr=False)
    _paused_until: float = field(default=0.0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def available(self) -> bool:
        # Интервал между запросами источник недоступным не делает — иначе
        # запрос по второму тикеру считался бы сбоем.
        if self._fails < self.max_fails:
            return True
        # Пауза, а не отключение навсегда: сеть могла пропасть на минуту,
        # и без второго шанса источник оставался бы мёртвым до перезапуска.
        if time.time() >= self._paused_until:
            self._fails = 0
            return True
        return False

    def paused_for(self) -> float:
        """Сколько секунд осталось до следующей попытки. 0 — источник доступен."""
        return max(0.0, self._paused_until - time.time())

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
            self._paused_until = 0.0
            return result
        except Exception:
            self._fails += 1
            if self._fails >= self.max_fails:
                self._paused_until = time.time() + self.cooldown
            raise

class Registry:
    def __init__(self):
        self._sources: dict[str, list[Source]] = {}

    def register(self, topic: str, source: Source):
        self._sources.setdefault(topic, []).append(source)
        self._sources[topic].sort(key=lambda s: s.priority)

    def fetch(self, topic: str, **kw) -> Any:
        sources = self._sources.get(topic, [])
        last_error, skipped = None, []
        for src in sources:
            if not src.available():
                skipped.append(src)
                continue
            try:
                return src.call(**kw)
            except Exception as e:
                last_error = e
                continue

        # Причину (прокси / 429 / тикер не найден) обязательно доносим наверх.
        if last_error is not None:
            raise RuntimeError(
                f"Все источники недоступны для '{topic}': {last_error}"
            ) from last_error
        # Ни один источник даже не опрашивался — значит все в паузе после
        # серии сбоев. Без этой ветки сообщение было бы вообще без причины.
        if skipped:
            wait = min(s.paused_for() for s in skipped)
            raise RuntimeError(
                f"Источники для '{topic}' временно отключены после серии "
                f"ошибок, повтор через {wait:.0f} с"
            )
        raise RuntimeError(f"Для '{topic}' не задано ни одного источника")

    def status(self) -> dict:
        out = {}
        for topic, sources in self._sources.items():
            out[topic] = [
                {"name": s.name, "fails": s._fails, "ok": s.available(),
                 "paused_for": round(s.paused_for())}
                for s in sources
            ]
        return out

# Глобальный реестр
REGISTRY = Registry()
