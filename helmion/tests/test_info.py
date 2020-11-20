import unittest

from helmion.info import RepositoryInfo


class TestInfo(unittest.TestCase):
    def setUp(self):
        self.rawinfo = {
            'apiVersion': 'v1',
            'entries': {
                'traefik': [{
                    'apiVersion': 'v2',
                    'appVersion': '2.3.1',
                    'created': '2020-11-04T08:02:58.708367931Z',
                    'description': 'A Traefik based Kubernetes ingress '
                                   'controller',
                    'digest': 'faf6f60da16462bf82112e1aaa72d726f6125f755c576590d98c0c2569d578b6',
                    'home': 'https://traefik.io/',
                    'icon': 'https://raw.githubusercontent.com/traefik/traefik/v2.3/docs/content/assets/img/traefik.logo.png',
                    'keywords': ['traefik', 'ingress'],
                    'maintainers': [{
                        'email': 'emile@vauge.com',
                        'name': 'emilevauge'
                    },
                    {
                        'email': 'daniel.tomcej@gmail.com',
                        'name': 'dtomcej'
                    },
                    {
                        'email': 'ldez@traefik.io',
                        'name': 'ldez'
                    }],
                    'name': 'traefik',
                    'sources': ['https://github.com/traefik/traefik',
                        'https://github.com/traefik/traefik-helm-chart'],
                    'type': 'application',
                    'urls': ['https://helm.traefik.io/traefik/traefik-9.10.1.tgz'],
                    'version': '9.10.1'
                },
                {
                    'apiVersion': 'v2',
                    'appVersion': '2.3.1',
                    'created': '2020-11-04T08:02:58.706928978Z',
                    'description': 'A Traefik based Kubernetes ingress '
                                   'controller',
                    'digest': '0a5bb66d56cb0502bad1472f41303c7b52b4f3b605e2d341644ee4a0b987052f',
                    'home': 'https://traefik.io/',
                    'icon': 'https://raw.githubusercontent.com/traefik/traefik/v2.3/docs/content/assets/img/traefik.logo.png',
                    'keywords': ['traefik', 'ingress'],
                    'maintainers': [{
                        'email': 'emile@vauge.com',
                        'name': 'emilevauge'
                    },
                        {
                            'email': 'daniel.tomcej@gmail.com',
                            'name': 'dtomcej'
                        },
                        {
                            'email': 'ldez@traefik.io',
                            'name': 'ldez'
                        }],
                    'name': 'traefik',
                    'sources': ['https://github.com/traefik/traefik',
                        'https://github.com/traefik/traefik-helm-chart'],
                    'type': 'application',
                    'urls': ['https://helm.traefik.io/traefik/traefik-9.10.0.tgz'],
                    'version': '9.10.0'
                },
                {
                    'apiVersion': 'v2',
                    'appVersion': '2.3.1',
                    'created': '2020-11-04T08:02:58.735677779Z',
                    'description': 'A Traefik based Kubernetes ingress '
                                   'controller',
                    'digest': '3f37ac274bbd730382592566ca4bc8d14b019a313dc6011e3a1519dc9a8ab980',
                    'home': 'https://traefik.io/',
                    'icon': 'https://raw.githubusercontent.com/traefik/traefik/v2.3/docs/content/assets/img/traefik.logo.png',
                    'keywords': ['traefik', 'ingress'],
                    'maintainers': [{
                        'email': 'emile@vauge.com',
                        'name': 'emilevauge'
                    },
                        {
                            'email': 'daniel.tomcej@gmail.com',
                            'name': 'dtomcej'
                        },
                        {
                            'email': 'ldez@traefik.io',
                            'name': 'ldez'
                        }],
                    'name': 'traefik',
                    'sources': ['https://github.com/traefik/traefik',
                        'https://github.com/traefik/traefik-helm-chart'],
                    'type': 'application',
                    'urls': ['https://helm.traefik.io/traefik/traefik-9.9.0.tgz'],
                    'version': '9.9.0'
                }
            ]}
        }

    def test_rawinfo(self):
        RepositoryInfo('http://example.com', rawinfo=self.rawinfo)

    def test_chartversion(self):
        info = RepositoryInfo('http://example.com', rawinfo=self.rawinfo)
        chartversion = info.chartVersion('traefik', '9.10.0')
        self.assertIsNotNone(chartversion)
        self.assertEqual(chartversion.version, '9.10.0')

    def test_chartversion_latest(self):
        info = RepositoryInfo('http://example.com', rawinfo=self.rawinfo)
        chartversion = info.chartVersion('traefik')
        self.assertIsNotNone(chartversion)
        self.assertEqual(chartversion.version, '9.10.1')

    def test_chartversion_simplespec(self):
        info = RepositoryInfo('http://example.com', rawinfo=self.rawinfo)
        chartversion = info.chartVersion('traefik', '<9.10.0')
        self.assertIsNotNone(chartversion)
        self.assertEqual(chartversion.version, '9.9.0')

    def test_chartversion_url(self):
        info = RepositoryInfo('http://example.com', rawinfo=self.rawinfo)
        chartversion = info.chartVersion('traefik')
        self.assertIsNotNone(chartversion)
        self.assertEqual(chartversion.fileUrl(), 'https://helm.traefik.io/traefik/traefik-9.10.1.tgz')
