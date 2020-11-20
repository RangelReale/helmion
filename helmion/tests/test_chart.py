import unittest

from jsonpatchext.mutators import InitItemMutator  # type: ignore

from helmion.chart import Request, Chart
from helmion.config import BoolFilter
from helmion.processor import DefaultProcessor


class TestInfo(unittest.TestCase):
    def setUp(self):
        self.req = Request(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
                           releasename='helmion-traefik', namespace='router')
        self.chart = Chart(self.req, data=[{
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

    def test_chart_filternamespaced(self):
        chart = self.chart.process(DefaultProcessor(namespaced_filter=BoolFilter.IF_TRUE))
        self.assertEqual(len(chart.data), 0)

    def test_chart_filternamespaced_after_add(self):
        chart = self.chart.process(DefaultProcessor(add_namespace=True, namespaced_filter=BoolFilter.IF_TRUE))
        self.assertEqual(len(chart.data), 3)
        for d in chart.data:
            self.assertNotIn(d['kind'], ['CustomResourceDefinition'])

    def test_chart_filterhook(self):
        chart = self.chart.process(DefaultProcessor(add_namespace=True, hook_filter=BoolFilter.IF_TRUE))
        self.assertEqual(len(chart.data), 1)
        for d in chart.data:
            self.assertIn(d['kind'], ['IngressRoute'])

    def test_chart_filterhook_list(self):
        chart = self.chart.process(DefaultProcessor(add_namespace=True, hook_filter=BoolFilter.IF_TRUE,
                                                    hook_filter_list=['pre-rollback']))
        self.assertEqual(len(chart.data), 0)

        chart = self.chart.process(DefaultProcessor(add_namespace=True, hook_filter=BoolFilter.IF_TRUE,
                                                    hook_filter_list=['post-upgrade']))
        self.assertEqual(len(chart.data), 1)

        chart = self.chart.process(DefaultProcessor(add_namespace=True, hook_filter=BoolFilter.IF_TRUE,
                                                    hook_filter_list=['post-upgrade', 'pre-rollback']))
        self.assertEqual(len(chart.data), 0)

        chart = self.chart.process(DefaultProcessor(add_namespace=True, hook_filter=BoolFilter.IF_TRUE,
                                                    hook_filter_list=['post-install', 'post-upgrade']))
        self.assertEqual(len(chart.data), 1)

    def test_chart_jsonpatch(self):
        chart = self.chart.process(DefaultProcessor(jsonpatches=[
            {
                'conditions': [[
                    {'op': 'check', 'path': '/kind', 'cmp': 'equals', 'value': 'Service'}
                ]],
                'patch': [
                    # Traefik Helm chart generates a null annotation field, must initialize it to a dict before merging.
                    {'op': 'mutate', 'path': '/metadata', 'mut': 'custom', 'mutator': InitItemMutator('annotations'),  'value': lambda: {}},
                    {
                        'op': 'merge', 'path': '/metadata', 'value': {
                            'annotations': {
                                'helmion.github.io/processed-by': 'helmion',
                            }
                        },
                    }
                ],
            }
        ]))
        for d in chart.data:
            if d['kind'] in ['Service']:
                self.assertIsNotNone(d['metadata']['annotations'])
                self.assertEqual(d['metadata']['annotations']['helmion.github.io/processed-by'], 'helmion')
            elif d['kind'] in ['IngressRoute']:
                self.assertNotIn('helmion.github.io/processed-by', d['metadata']['annotations'])
            else:
                self.assertTrue('annotations' not in d['metadata'] or d['metadata']['annotations'] is None)

    def test_chart_filterfunc(self):
        chart = self.chart.process(DefaultProcessor(filterfunc=lambda x: x['kind'] in ['Service', 'IngressRoute']))
        for d in chart.data:
            self.assertTrue(d['kind'] in ['Service', 'IngressRoute'])
