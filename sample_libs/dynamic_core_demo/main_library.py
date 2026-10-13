
from robotlibcore import DynamicCore
from .library_a import LibraryA
from .library_b import LibraryB

class MainLibrary(DynamicCore):
    """Aggregated dynamic library."""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"

    def __init__(self):
        lib_a = LibraryA()
        lib_b = LibraryB()
        libraries = [lib_a, lib_b]
        # include docs of libraries
        self.__doc__ = "\n\n".join([
            LibraryA.__doc__ or "",
            LibraryB.__doc__ or "",
        ])
        super().__init__(libraries)
