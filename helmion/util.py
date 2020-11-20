from typing import Tuple
from urllib.parse import urlparse


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


helm_hook_anno = 'helm.sh/hook'
