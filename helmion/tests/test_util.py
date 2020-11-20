import unittest

from helmion.util import parse_apiversion


class TestUtil(unittest.TestCase):
    def test_parse_apiversion(self):
        self.assertEqual(parse_apiversion('apiextensions.k8s.io/v1beta1'), ('apiextensions.k8s.io', 'v1beta1'))
        self.assertEqual(parse_apiversion('apps/v1'), ('apps', 'v1'))
        self.assertEqual(parse_apiversion('v1'), ('', 'v1'))
