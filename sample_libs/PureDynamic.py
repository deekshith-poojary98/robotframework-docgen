
class PureDynamic:
    """Pure dynamic RF library (get_keyword_names)."""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def get_keyword_names(self):
        return ["Do Thing", "Say Hello"]

    def run_keyword(self, name, args, kwargs):
        return None

    def get_keyword_arguments(self, name):
        if name == "Do Thing":
            return ["value"]
        return []

    def get_keyword_documentation(self, name):
        if name == "__intro__":
            return self.__doc__
        if name == "Do Thing":
            return "Do a thing with value.\n\n**Arguments:**\n- `value`: payload"
        if name == "Say Hello":
            return "Say hello."
        return ""

    def get_keyword_tags(self, name):
        return ["dynamic"] if name == "Do Thing" else []
