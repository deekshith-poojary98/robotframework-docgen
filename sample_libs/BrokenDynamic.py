
from robot.api.deco import keyword
from robotlibcore import DynamicCore

class LibraryA:
    """A docs."""
    @keyword
    def alpha(self):
        """Alpha kw."""
        pass

class LibraryB:
    """B docs."""
    @keyword
    def beta(self):
        """Beta kw."""
        pass

class BrokenDynamic(DynamicCore):
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    def __init__(self):
        libA = LibraryA  # class, not instance — as in the issue
        libB = LibraryB
        __doc__ = "\n\n".join([libA.__doc__, libB.__doc__])
        super().__init__([libA, libB])
