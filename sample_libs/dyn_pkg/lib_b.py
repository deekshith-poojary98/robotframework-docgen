
from robot.api.deco import keyword
class LibraryB:
    """B docs."""
    @keyword
    def compute_from_b(self, x: int, y: int = 1) -> int:
        """Add in B."""
        return x + y
