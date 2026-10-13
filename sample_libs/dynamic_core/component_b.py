"""Component B for the DynamicCore demo."""

from robot.api.deco import keyword


class ComponentB:
    """Keywords contributed by component B."""

    @keyword
    def compute_from_b(self, x: int, y: int = 1) -> int:
        """Add two numbers in component B.

        **Arguments:**
        - `x`: Left operand
        - `y`: Right operand (default ``1``)
        """
        return x + y

    @keyword("Echo From B")
    def echo_from_b(self, message: str) -> str:
        """Echo a message via component B."""
        return message
