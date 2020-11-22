import os
import unittest

import semantic_version

from helmion.helmchart import HelmRequest
from helmion.info import RepositoryInfo

SLOW_TESTS = int(os.getenv('SLOW_TESTS', '0'))


@unittest.skipIf(not SLOW_TESTS, "slow")
class TestSlow(unittest.TestCase):
    def test_info_traefik(self):
        repoinfo = RepositoryInfo('https://helm.traefik.io/traefik')
        self.assertEqual(repoinfo.mustChartVersion('traefik', '9.10.1').version, '9.10.1')
        self.assertEqual(repoinfo.mustChartVersion('traefik', '9.10.1').digest, 'faf6f60da16462bf82112e1aaa72d726f6125f755c576590d98c0c2569d578b6')
        self.assertEqual(repoinfo.mustChartVersion('traefik', '<9.9.*').version, '9.8.4')

    def test_chart_traefik(self):
        req = HelmRequest(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
                          releasename='helmion-traefik', namespace='router')
        res = req.generate()
        self.assertEqual(len([x for x in res.data if x['kind'] == 'Deployment']), 1)

    def test_chart_deps_compat(self):
        repoinfo = RepositoryInfo('https://grafana.github.io/loki/charts')
        chartversion = repoinfo.mustChartVersion('loki-stack', '2.0.3')
        self.assertEqual(chartversion.version, '2.0.3')
        depchartversion = chartversion.getDependencyChart('fluent-bit')
        cv = semantic_version.SimpleSpec('^2.0.0')
        self.assertTrue(cv.match(semantic_version.Version(depchartversion.version)))
