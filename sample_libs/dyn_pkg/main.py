
from robotlibcore import DynamicCore
from sample_libs.dyn_pkg.lib_a import LibraryA
from sample_libs.dyn_pkg.lib_b import LibraryB

class MainLibrary(DynamicCore):
    """Aggregated via DynamicCore."""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"
    def __init__(self):
        libs = [LibraryA(), LibraryB()]
        MainLibrary.__doc__ = "\n\n".join([
            LibraryA.__doc__ or "",
            LibraryB.__doc__ or "",
            "MainLibrary aggregates A and B.",
        ])
        super().__init__(libs)
