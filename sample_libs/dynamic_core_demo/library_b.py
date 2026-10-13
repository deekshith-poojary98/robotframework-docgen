
from robot.api.deco import keyword

class LibraryB:
    """Library B docs."""
    @keyword
    def compute_from_b(self, x: int, y: int = 1) -> int:
        """Add two numbers in B."""
        return x + y
