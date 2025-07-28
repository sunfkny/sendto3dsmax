class UnsupportedFileTypeError(RuntimeError):
    pass


class MaxNotFoundError(RuntimeError):
    pass


class ElementNotFoundError(RuntimeError):
    pass


class EditBoxNotFoundError(ElementNotFoundError):
    pass


class StatusPanelFoundError(ElementNotFoundError):
    pass


class MaxNotRespondingError(ElementNotFoundError):
    pass
