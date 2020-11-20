import os
import unittest

from helmion.chart import Request
from helmion.info import RepositoryInfo

SLOW_TESTS = int(os.getenv('SLOW_TESTS', '0'))


@unittest.skipIf(not SLOW_TESTS, "slow")
class TestSlow(unittest.TestCase):
    def test_info_traefik(self):
        repoinfo = RepositoryInfo('https://helm.traefik.io/traefik')
        self.assertEqual(repoinfo.mustChartVersion('traefik', '9.10.1').version, '9.10.1')
        self.assertEqual(repoinfo.mustChartVersion('traefik', '9.10.1').digest, 'faf6f60da16462bf82112e1aaa72d726f6125f755c576590d98c0c2569d578b6')

    def test_chart_traefik(self):
        req = Request(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
                      releasename='helmion-traefik', namespace='router')
        res = req.generate()
        self.assertEqual(len([x for x in res.data if x['kind'] == 'Deployment']), 1)
