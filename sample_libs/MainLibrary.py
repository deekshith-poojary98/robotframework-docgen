
from robot.api.deco import keyword
from robotlibcore import DynamicCore

class LibraryA:
    """Library A docs."""
    @keyword
    def greet_from_a(self, name: str = "world") -> str:
        """Say hello from A."""
        return f"A:{name}"

class LibraryB:
    """Library B docs."""
    @keyword
    def compute_from_b(self, x: int, y: int = 1) -> int:
        """Add two numbers in B."""
        return x + y

class MainLibrary(DynamicCore):
    """Main dynamic library aggregating A and B."""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"

    def __init__(self):
        lib_a = LibraryA()
        lib_b = LibraryB()
        MainLibrary.__doc__ = "\n\n".join([
            LibraryA.__doc__ or "",
            LibraryB.__doc__ or "",
            "MainLibrary aggregates A and B via DynamicCore.",
        ])
        super().__init__([lib_a, lib_b])
