import unittest

from jsonpatchext.mutators import InitItemMutator  # type: ignore

from helmion.helmchart import HelmRequest, HelmChart
from helmion.config import BoolFilter
from helmion.processor import DefaultProcessor


class TestInfo(unittest.TestCase):
    def setUp(self):
        self.req = HelmRequest(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
                               releasename='helmion-traefik', namespace='router')
        self.chart = HelmChart(request=self.req, data=[{
            'apiVersion': 'apiextensions.k8s.io/v1beta1',
            'kind': 'CustomResourceDefinition',
            'metadata': {'name': 'ingressroutes.traefik.containo.us'},
            'spec': {
                'group': 'traefik.containo.us',
                'names': {
                    'kind': 'IngressRoute',
                    'plural': 'ingressroutes',
                    'singular': 'ingressroute'
                },
                'scope': 'Namespaced',
                'version': 'v1alpha1'
            }
        }, {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {
                'annotations': None,
                'labels': {
                    'app.kubernetes.io/instance': 'helmion-traefik',
                    'app.kubernetes.io/managed-by': 'Helm',
                    'app.kubernetes.io/name': 'traefik',
                    'helm.sh/chart': 'traefik-9.10.1'
                },
                'name': 'helmion-traefik'
            }
        }, {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'annotations': None,
                'labels': {
                    'app.kubernetes.io/instance': 'helmion-traefik',
                    'app.kubernetes.io/managed-by': 'Helm',
                    'app.kubernetes.io/name': 'traefik',
                    'helm.sh/chart': 'traefik-9.10.1'
                },
                'name': 'helmion-traefik'
            },
            'spec': {
                'ports': [{
                    'name': 'web',
                    'port': 80,
                    'protocol': 'TCP',
                    'targetPort': 'web'
                },
                {
                    'name': 'websecure',
                    'port': 443,
                    'protocol': 'TCP',
                    'targetPort': 'websecure'
                }],
                'selector': {
                    'app.kubernetes.io/instance': 'helmion-traefik',
                    'app.kubernetes.io/name': 'traefik'
                },
                'type': 'ClusterIP'
            }
        }, {
            'apiVersion': 'traefik.containo.us/v1alpha1',
            'kind': 'IngressRoute',
            'metadata': {
                'annotations': {'helm.sh/hook': 'post-install,post-upgrade'},
                'labels': {
                    'app.kubernetes.io/instance': 'helmion-traefik',
                    'app.kubernetes.io/managed-by': 'Helm',
                    'app.kubernetes.io/name': 'traefik',
                    'helm.sh/chart': 'traefik-9.10.1'
                },
                'name': 'helmion-traefik-dashboard'
            },
            'spec': {
                'entryPoints': ['traefik'],
                'routes': [{
                    'kind': 'Rule',
                    'match': 'PathPrefix(`/dashboard`) || PathPrefix(`/api`)',
                    'services': [{
                        'kind': 'TraefikService',
                        'name': 'api@internal'
                    }]
                }]
            }
        }])

    def test_chart_addnamespace(self):
        chart = self.chart.process(DefaultProcessor(add_namespace=True))
        for d in chart.data:
            if d['kind'] in ['CustomResourceDefinition']:
                self.assertFalse('namespace' in d['metadata'])
            else:
                self.assertTrue('namespace' in d['metadata'])
                self.assertEqual(d['metadata']['namespace'], self.req.namespace)
