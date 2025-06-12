class BaseError(Exception):
    pass


class UnsupportedFileTypeError(BaseError):
    pass


class MaxNotFoundError(BaseError):
    pass


class MultipleinstancesError(BaseError):
    pass


class ListenerWindowNotFoundError(BaseError):
    pass
