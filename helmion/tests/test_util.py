import unittest

from helmion.exception import ParamError
from helmion.util import parse_apiversion, resolve_dependency_url


class TestUtil(unittest.TestCase):
    def test_parse_apiversion(self):
        self.assertEqual(parse_apiversion('apiextensions.k8s.io/v1beta1'), ('apiextensions.k8s.io', 'v1beta1'))
        self.assertEqual(parse_apiversion('apps/v1'), ('apps', 'v1'))
        self.assertEqual(parse_apiversion('v1'), ('', 'v1'))

    def test_resolve_dependency_url(self):
        self.assertEqual(resolve_dependency_url(
            'https://github.com/grafana/loki/blob/master/production/helm/loki-stack', 'https://helm.elastic.co'),
        'https://helm.elastic.co')

        self.assertEqual(resolve_dependency_url(
            'https://github.com/grafana/loki/blob/master/production/helm/loki-stack', 'file://../fluent-bit'),
        'https://github.com/grafana/loki/blob/master/production/helm/loki-stack')

        with self.assertRaises(ParamError):
            resolve_dependency_url('https://github.com/grafana/loki/blob/master/production/helm/loki-stack', 'file:///x/y/z')
