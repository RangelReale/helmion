class HelmionException(Exception):
    pass


class HelmError(HelmionException):
    def __init__(self, *args, cmd=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = cmd


class ParamError(HelmionException):
    pass


class ConfigurationError(HelmionException):
    pass


class InputOutputError(HelmionException):
    pass


class NetworkError(HelmionException):
    pass
