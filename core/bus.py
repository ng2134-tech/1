# -*- coding: utf-8 -*-
# Thread-safe message bus: pub/sub между агентами.
# Один WebSocket-паттерн (из архитектуры TR) — адаптирован для in-process.
import queue, threading
from collections import defaultdict
from typing import Callable, Any

class Bus:
    def __init__(self):
        self._subs: dict[str, list[Callable]] = defaultdict(list)
        self._q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._running = False

    def subscribe(self, topic: str, cb: Callable):
        with self._lock:
            self._subs[topic].append(cb)

    def publish(self, topic: str, data: Any):
        self._q.put((topic, data))

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        self._q.put(("__stop__", None))

    def _loop(self):
        while self._running:
            try:
                topic, data = self._q.get(timeout=1)
                if topic == "__stop__":
                    break
                with self._lock:
                    cbs = list(self._subs.get(topic, []))
                for cb in cbs:
                    try:
                        cb(data)
                    except Exception:
                        pass
            except queue.Empty:
                continue

# Глобальная шина
BUS = Bus()
