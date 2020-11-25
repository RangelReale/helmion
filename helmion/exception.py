class HelmionException(Exception):
    pass


class HelmError(HelmionException):
    def __init__(self, *args, cmd=None, stdout=None, stderr=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr


class ParamError(HelmionException):
    pass


class ConfigurationError(HelmionException):
    pass


class InputOutputError(HelmionException):
    pass


class NetworkError(HelmionException):
    pass
