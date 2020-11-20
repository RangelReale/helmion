from typing import Tuple
from urllib.parse import urlparse

import yaml
from yaml.reader import Reader


def remove_prefix(text, prefix):
    """Remove text prefix"""
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def is_absolute(url):
    """Checks whether the url is absolute"""
    return bool(urlparse(url).netloc)


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
