class EventBus:
    def __init__(self):
        self._handlers = {}

    def on(self, evt: str, fn):
        self._handlers.setdefault(evt, []).append(fn)

    def emit(self, evt: str, **data):
        for fn in self._handlers.get(evt, []):
            try:
                fn(**data)
            except Exception:
                pass

