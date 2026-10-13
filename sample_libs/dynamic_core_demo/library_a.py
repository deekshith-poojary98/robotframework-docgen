
from robot.api.deco import keyword

class LibraryA:
    """Library A docs."""
    @keyword
    def greet_from_a(self, name: str = "world") -> str:
        """Say hello from A.

        **Arguments:**
        - `name`: Who to greet
        """
        return f"A:{name}"
