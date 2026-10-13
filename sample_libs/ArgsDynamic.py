
from robot.api.deco import keyword
from robotlibcore import DynamicCore

class _Inner:
    @keyword
    def ping(self):
        """Ping keyword."""
        return "pong"

class ArgsDynamic(DynamicCore):
    """Needs a required init arg — Libdoc may fail init."""
    def __init__(self, base_url: str):
        self.base_url = base_url
        super().__init__([_Inner()])
