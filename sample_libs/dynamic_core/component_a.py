"""Component A for the DynamicCore demo."""

from robot.api.deco import keyword


class ComponentA:
    """Keywords contributed by component A."""

    @keyword
    def greet_from_a(self, name: str = "world") -> str:
        """Say hello from component A.

        **Arguments:**
        - `name`: Who to greet
        """
        return f"A:{name}"

    @keyword
    def ping_a(self) -> str:
        """Simple ping from A."""
        return "pong-a"
