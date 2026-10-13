
from robot.api.deco import keyword
class LibraryA:
    """A docs."""
    @keyword
    def greet_from_a(self, name: str = "world") -> str:
        """Say hello from A."""
        return f"A:{name}"
