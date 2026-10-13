
from robotlibcore import DynamicCore
from sample_libs.dyn_pkg.lib_a import LibraryA
from sample_libs.dyn_pkg.lib_b import LibraryB

class IssueStyleMain(DynamicCore):
    """Issue-style DynamicCore aggregator."""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"
    def __init__(self):
        lib_a = LibraryA()
        lib_b = LibraryB()
        IssueStyleMain.__doc__ = "\n\n".join([
            LibraryA.__doc__ or "",
            LibraryB.__doc__ or "",
        ])
        super().__init__([lib_a, lib_b])
