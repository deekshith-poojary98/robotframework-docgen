"""DynamicCore aggregator matching GitHub issue #7's intended pattern."""

from robotlibcore import DynamicCore

from .component_a import ComponentA
from .component_b import ComponentB


class MainLibrary(DynamicCore):
    """Aggregated dynamic library built with ``robotlibcore.DynamicCore``.

    Keywords come from component libraries registered at init time — the
    aggregator itself has no ``@keyword`` methods.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"

    def __init__(self):
        components = [ComponentA(), ComponentB()]
        # Merge component docs into the aggregate intro (issue #7 pattern).
        MainLibrary.__doc__ = "\n\n".join(
            [
                (ComponentA.__doc__ or "").strip(),
                (ComponentB.__doc__ or "").strip(),
                "MainLibrary aggregates A and B via DynamicCore.",
            ]
        )
        super().__init__(components)
