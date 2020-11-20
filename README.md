# Helmion

[![PyPI version](https://img.shields.io/pypi/v/helmion.svg)](https://pypi.python.org/pypi/helmion/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/helmion.svg)](https://pypi.python.org/pypi/helmion/)

Helmion is a python library to download and customize [Helm](https://helm.sh/) charts.

* Website: https://github.com/RangelReale/helmion
* Repository: https://github.com/RangelReale/helmion.git
* Documentation: https://helmion.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/helmion

### Example: chart

```python
import pprint

from jsonpatchext.mutators import InitItemMutator  # type: ignore

from helmion.chart import Request, Splitter, ProcessorChain
from helmion.config import BoolFilter
from helmion.processor import DefaultProcessor, FilterRemoveHelmData, FilterCRDs, DefaultSplitter, ProcessorSplitter

req = Request(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
              releasename='helmion-traefik', namespace='router', values={
        'service': {
            'type': 'ClusterIP',
        }
    })

reqfilter = DefaultProcessor(add_namespace=True, namespaced_filter=BoolFilter.ALL, hook_filter=BoolFilter.ALL, jsonpatches=[
    {
        'conditions': [[
            {'op': 'check', 'path': '/kind', 'cmp': 'equals', 'value': 'Service'}
        ], [
            {'op': 'check', 'path': '/kind', 'cmp': 'equals', 'value': 'ServiceAccount'}
        ], [
            {'op': 'check', 'path': '/kind', 'cmp': 'equals', 'value': 'ClusterRoleBinding'}
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
])

res = req.generate(ProcessorChain(
    reqfilter,
    FilterRemoveHelmData(only_exlcusive=False, remove_hooks=False)
))

for d in res.data:
    pprint.pprint(d)

# Split charts by CRD

print('')
print('Split charts by CRDs')
print('====================')

reqsplitter = ProcessorSplitter(processors={
    'crds': FilterCRDs(),
    'default': FilterCRDs(invert_filter=True),
})

mres = res.split(list(reqsplitter.processors.keys()), reqsplitter)

for category, category_chart in mres.items():
    print('')
    print('*** {} ***'.format(category))
    for d in category_chart.data:
        pprint.pprint(d)


# Split and filter by Kind

print('')
print('Split Deployment and ServiceAccount charts')
print('==========================================')

reqsplitter2 = DefaultSplitter(categoryfunc=lambda x: 'deployment' if x['kind'] == 'Deployment' else 'serviceaccount' if x['kind'] == 'ServiceAccount' else False)

mres = res.split(['deployment', 'serviceaccount'], reqsplitter2)

for category, category_chart in mres.items():
    print('')
    print('*** {} ***'.format(category))
    for d in category_chart.data:
        pprint.pprint(d)
```

Output:

```text
{'apiVersion': 'apiextensions.k8s.io/v1beta1',
 'kind': 'CustomResourceDefinition',
 'metadata': {'name': 'ingressroutes.traefik.containo.us',
              'namespace': 'router'},
 'spec': {'group': 'traefik.containo.us',
          'names': {'kind': 'IngressRoute',
                    'plural': 'ingressroutes',
                    'singular': 'ingressroute'},
          'scope': 'Namespaced',
          'version': 'v1alpha1'}}
{'apiVersion': 'apiextensions.k8s.io/v1beta1',
 'kind': 'CustomResourceDefinition',
 'metadata': {'name': 'ingressroutetcps.traefik.containo.us',
              'namespace': 'router'},
 'spec': {'group': 'traefik.containo.us',
          'names': {'kind': 'IngressRouteTCP',
                    'plural': 'ingressroutetcps',
                    'singular': 'ingressroutetcp'},
          'scope': 'Namespaced',
          'version': 'v1alpha1'}}

<...more...>

Split charts by CRDs
====================

*** crds ***
{'apiVersion': 'apiextensions.k8s.io/v1beta1',
 'kind': 'CustomResourceDefinition',
 'metadata': {'name': 'ingressroutes.traefik.containo.us',
              'namespace': 'router'},
 'spec': {'group': 'traefik.containo.us',
          'names': {'kind': 'IngressRoute',
                    'plural': 'ingressroutes',
                    'singular': 'ingressroute'},
          'scope': 'Namespaced',
          'version': 'v1alpha1'}}
{'apiVersion': 'apiextensions.k8s.io/v1beta1',
 'kind': 'CustomResourceDefinition',
 'metadata': {'name': 'ingressroutetcps.traefik.containo.us',
              'namespace': 'router'},
 'spec': {'group': 'traefik.containo.us',
          'names': {'kind': 'IngressRouteTCP',
                    'plural': 'ingressroutetcps',
                    'singular': 'ingressroutetcp'},
          'scope': 'Namespaced',
          'version': 'v1alpha1'}}

<...more...>

*** default ***
{'apiVersion': 'v1',
 'kind': 'ServiceAccount',
 'metadata': {'annotations': {'helmion.github.io/processed-by': 'helmion'},
              'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                         'app.kubernetes.io/name': 'traefik'},
              'name': 'helmion-traefik',
              'namespace': 'router'}}
{'apiVersion': 'rbac.authorization.k8s.io/v1',
 'kind': 'ClusterRole',
 'metadata': {'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                         'app.kubernetes.io/name': 'traefik'},
              'name': 'helmion-traefik',
              'namespace': 'router'},
 'rules': [{'apiGroups': [''],
            'resources': ['services', 'endpoints', 'secrets'],
            'verbs': ['get', 'list', 'watch']},
           {'apiGroups': ['extensions', 'networking.k8s.io'],
            'resources': ['ingresses', 'ingressclasses'],
            'verbs': ['get', 'list', 'watch']},
           {'apiGroups': ['extensions', 'networking.k8s.io'],
            'resources': ['ingresses/status'],
            'verbs': ['update']},
           {'apiGroups': ['traefik.containo.us'],
            'resources': ['ingressroutes',
                          'ingressroutetcps',
                          'ingressrouteudps',
                          'middlewares',
                          'tlsoptions',
                          'tlsstores',
                          'traefikservices'],
            'verbs': ['get', 'list', 'watch']}]}

<...more...>

Split Deployment and ServiceAccount charts
==========================================

*** deployment ***
{'apiVersion': 'apps/v1',
 'kind': 'Deployment',
 'metadata': {'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                         'app.kubernetes.io/name': 'traefik'},
              'name': 'helmion-traefik',
              'namespace': 'router'},
 'spec': {'replicas': 1,
          'selector': {'matchLabels': {'app.kubernetes.io/instance': 'helmion-traefik',
                                       'app.kubernetes.io/name': 'traefik'}},
          'strategy': {'rollingUpdate': {'maxSurge': 1, 'maxUnavailable': 1},
                       'type': 'RollingUpdate'},
          'template': {'metadata': {'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                                               'app.kubernetes.io/name': 'traefik'}},
                       'spec': {'containers': [{'args': ['--global.checknewversion',
                                                         '--global.sendanonymoususage',
                                                         '--entryPoints.traefik.address=:9000/tcp',
                                                         '--entryPoints.web.address=:8000/tcp',
                                                         '--entryPoints.websecure.address=:8443/tcp',
                                                         '--api.dashboard=true',
                                                         '--ping=true',
                                                         '--providers.kubernetescrd',
                                                         '--providers.kubernetesingress'],
                                                'image': 'traefik:2.3.1',
                                                'imagePullPolicy': 'IfNotPresent',
                                                'livenessProbe': {'failureThreshold': 3,
                                                                  'httpGet': {'path': '/ping',
                                                                              'port': 9000},
                                                                  'initialDelaySeconds': 10,
                                                                  'periodSeconds': 10,
                                                                  'successThreshold': 1,
                                                                  'timeoutSeconds': 2},
                                                'name': 'helmion-traefik',
                                                'ports': [{'containerPort': 9000,
                                                           'name': 'traefik',
                                                           'protocol': 'TCP'},
                                                          {'containerPort': 8000,
                                                           'name': 'web',
                                                           'protocol': 'TCP'},
                                                          {'containerPort': 8443,
                                                           'name': 'websecure',
                                                           'protocol': 'TCP'}],
                                                'readinessProbe': {'failureThreshold': 1,
                                                                   'httpGet': {'path': '/ping',
                                                                               'port': 9000},
                                                                   'initialDelaySeconds': 10,
                                                                   'periodSeconds': 10,
                                                                   'successThreshold': 1,
                                                                   'timeoutSeconds': 2},
                                                'resources': None,
                                                'securityContext': {'capabilities': {'drop': ['ALL']},
                                                                    'readOnlyRootFilesystem': True,
                                                                    'runAsGroup': 65532,
                                                                    'runAsNonRoot': True,
                                                                    'runAsUser': 65532},
                                                'volumeMounts': [{'mountPath': '/data',
                                                                  'name': 'data'},
                                                                 {'mountPath': '/tmp',
                                                                  'name': 'tmp'}]}],
                                'hostNetwork': False,
                                'securityContext': {'fsGroup': 65532},
                                'serviceAccountName': 'helmion-traefik',
                                'terminationGracePeriodSeconds': 60,
                                'volumes': [{'emptyDir': {}, 'name': 'data'},
                                            {'emptyDir': {}, 'name': 'tmp'}]}}}}

*** serviceaccount ***
{'apiVersion': 'v1',
 'kind': 'ServiceAccount',
 'metadata': {'annotations': {'helmion.github.io/processed-by': 'helmion'},
              'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                         'app.kubernetes.io/name': 'traefik'},
              'name': 'helmion-traefik',
              'namespace': 'router'}}
```

### Example: info

```python
from helmion.info import RepositoryInfo

repository_url = 'https://helm.traefik.io/traefik'
chart_name = 'traefik'
chart_version = '9.10.1'

repoinfo = RepositoryInfo(repository_url)

print('Repository charts')
print('=================')
for ci in repoinfo.entries.values():
    print('Chart: {}'.format(ci.name))
    if ci.latest is not None:
        print('Description: {}'.format(ci.latest.description))
        print('Latest: {}'.format(ci.latest.version))
    for r in ci.versions:
        print('\trelease: {}'.format(r.version))


print('')
print('Chart.yaml')
print('==========')

# pprint.pprint(repoinfo.chartVersion(chart_name, chart_version).getChartFile())
print(repoinfo.mustChartVersion(chart_name, chart_version).getArchiveFile('Chart.yaml'))


print('')
print('values.yaml')
print('===========')

# pprint.pprint(repoinfo.chartVersion(chart_name, chart_version).getValuesFile())
print(repoinfo.mustChartVersion(chart_name, chart_version).getArchiveFile('values.yaml'))


print('')
print('Chart file contents')
print('===================')
with repoinfo.mustChartVersion(chart_name, chart_version).fileOpen() as tar_file:
    for fname in tar_file.getnames():
        print("- {}".format(fname))
```

Output:

```text
Repository charts
=================
Chart: traefik
Description: A Traefik based Kubernetes ingress controller
Latest: 9.11.0
	release: 9.11.0
	release: 9.10.2
	release: 9.10.1
	release: 9.10.0
	release: 9.9.0
	release: 9.8.4
	release: 9.8.3
	release: 9.8.2
	release: 9.8.1
<...more...>

Chart.yaml
==========
apiVersion: v2
appVersion: 2.3.1
description: A Traefik based Kubernetes ingress controller
home: https://traefik.io/
icon: https://raw.githubusercontent.com/traefik/traefik/v2.3/docs/content/assets/img/traefik.logo.png
keywords:
- traefik
- ingress
maintainers:
- email: emile@vauge.com
  name: emilevauge
- email: daniel.tomcej@gmail.com
  name: dtomcej
- email: ldez@traefik.io
  name: ldez
name: traefik
sources:
- https://github.com/traefik/traefik
- https://github.com/traefik/traefik-helm-chart
type: application
version: 9.10.1


values.yaml
===========
# Default values for Traefik
image:
  name: traefik
  # defaults to appVersion
  tag: ""
  pullPolicy: IfNotPresent

#
# Configure the deployment
#
deployment:
  enabled: true
  # Number of pods of the deployment
  replicas: 1
  # Additional deployment annotations (e.g. for jaeger-operator sidecar injection)
  annotations: {}
<...more...>

Chart file contents
===================
- traefik/Chart.yaml
- traefik/values.yaml
- traefik/templates/_helpers.tpl
- traefik/templates/dashboard-hook-ingressroute.yaml
- traefik/templates/deployment.yaml
- traefik/templates/hpa.yaml
- traefik/templates/ingressclass.yaml
- traefik/templates/poddisruptionbudget.yaml
<...more...>
```

### Credits

based on

Based on [MichaelVL/kubernetes-deploy-tools](https://github.com/MichaelVL/kubernetes-deploy-tools).

## Author

Rangel Reale (rangelreale@gmail.com)
