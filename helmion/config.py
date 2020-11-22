from enum import Enum
from typing import Optional, Sequence, Any, Dict

import yaml

from helmion.exception import InputOutputError


class Config:
    """
    Global configuration.

    :param parse_list_resource: whether to parse ```List``` Kubernetes resource and process each
        item separatelly. See `Any official docs around Kind: List? <https://github.com/kubernetes/kubectl/issues/837>`_.
    """
    parse_list_resource: bool

    def __init__(self, parse_list_resource: bool = True):
        self.parse_list_resource = parse_list_resource

    def yaml_load(self, source: Any) -> Any:
        try:
            return yaml.load(source, Loader=yaml.SafeLoader)
        except yaml.YAMLError as e:
            raise InputOutputError(str(e)) from e

    def yaml_load_all(self, source: Any) -> Any:
        try:
            return yaml.load_all(source, Loader=yaml.SafeLoader)
        except yaml.YAMLError as e:
            raise InputOutputError(str(e)) from e

    def yaml_dump(self, source: Any) -> Any:
        try:
            return yaml.dump(source, Dumper=yaml.Dumper, sort_keys=False)
        except yaml.YAMLError as e:
            raise InputOutputError(str(e)) from e

    def yaml_dump_all(self, source: Any) -> Any:
        try:
            return yaml.dump_all(source, Dumper=yaml.Dumper, sort_keys=False)
        except yaml.YAMLError as e:
            raise InputOutputError(str(e)) from e


class BoolFilter(Enum):
    """
    Filter to use for boolean options.
    """
    ALL = 0
    IF_TRUE = 1
    IF_FALSE = 2
