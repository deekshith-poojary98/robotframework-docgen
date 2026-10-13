"""DynamicCore library whose constructor requires arguments."""

from robot.api.deco import keyword
from robotlibcore import DynamicCore


class _ArgsHelpers:
    @keyword
    def ping(self) -> str:
        """Return ``pong`` using the configured base URL context."""
        return "pong"


class ArgsLibrary(DynamicCore):
    """Dynamic library that requires a ``base_url`` import argument."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"

    def __init__(self, base_url: str):
        self.base_url = base_url
        super().__init__([_ArgsHelpers()])
