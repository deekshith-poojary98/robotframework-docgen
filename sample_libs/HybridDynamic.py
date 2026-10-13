
from robot.api.deco import keyword
from robotlibcore import DynamicCore

class _Helpers:
    @keyword
    def helper_only(self, x):
        """Helper keyword."""
        return x

class HybridDynamic(DynamicCore):
    """Hybrid docs."""
    ROBOT_LIBRARY_VERSION = "2.0.0"
    def __init__(self, prefix: str = "x"):
        self.prefix = prefix
        super().__init__([_Helpers()])
