import pathlib
from typing import Tuple, Optional
from urllib.parse import urlparse

import yaml
from yaml.reader import Reader

from helmion.exception import ParamError


def remove_prefix(text, prefix):
    """Remove text prefix"""
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def is_absolute_url(url):
    """Checks whether the url is absolute"""
    return bool(urlparse(url).netloc)


def resolve_dependency_url(base_url: str, url: str) -> str:
    if not is_absolute_url(url):
        raise ParamError('Url "{}" is not absolute'.format(url))
    u = urlparse(url)
    if u.scheme in ['http', 'https']:
        return url
    elif u.scheme in ['file']:
        # Special case for some existing dependency urls
        # File urls are being deprecated
        if url.startswith('file://./'):
            return base_url
        elif url.startswith('file://../'):
            return base_url
        else:
            raise ParamError('Unsupported file url: "{}"'.format(url))
    else:
        raise ParamError('Unknown url scheme: "{}"'.format(url))


def parse_apiversion(apiversion: str) -> Tuple[str, str]:
    """Parse ```apiVersion``` into a 2-item tuple."""
    p = apiversion.split('/', 1)
    if len(p) == 1:
        return '', p[0]
    return p[0], p[1]


def yaml_strip_invalid(s: str) -> str:
    """Remove yaml non-printable characters from string"""
    invalid_chars = ['\u0080', '\u0099']
    invalid_table = str.maketrans({k: '_' for k in invalid_chars})
    return s.translate(invalid_table)




helm_hook_anno = 'helm.sh/hook'
