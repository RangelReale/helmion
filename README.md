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

from jsonpatchext.mutators import InitItemMutator

from helmion.chart import Request, Splitter, ProcessorChain
from helmion.config import BoolFilter
from helmion.processor import DefaultProcessor, FilterRemoveHelmData, FilterCRDs

req = Request(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
              releasename='helmion-traefik', namespace='router')

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

reqsplitter = Splitter(categories={
    'crds': FilterCRDs(),
    'default': FilterCRDs(invert_filter=True),
})

mres = res.split(reqsplitter)

for category, category_chart in mres.items():
    print('')
    print('*** {} ***'.format(category))
    for d in category_chart.data:
        pprint.pprint(d)


# Split Service charts

print('')
print('Split Service and ServiceAccount charts')
print('=======================================')

reqsplitter = Splitter(categories={
    'service': None,
    'serviceaccount': None,
}, categoryfunc=lambda x: 'service' if x['kind'] == 'Service' else 'serviceaccount' if x['kind'] == 'ServiceAccount' else False)

mres = res.split(reqsplitter)

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
{'apiVersion': 'apiextensions.k8s.io/v1beta1',
 'kind': 'CustomResourceDefinition',
 'metadata': {'name': 'ingressrouteudps.traefik.containo.us',

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

<...more...>

Split Service and ServiceAccount charts
=======================================

*** service ***
{'apiVersion': 'v1',
 'kind': 'ServiceAccount',
 'metadata': {'annotations': {'helmion.github.io/processed-by': 'helmion'},
              'labels': {'app.kubernetes.io/instance': 'helmion-traefik',
                         'app.kubernetes.io/name': 'traefik'},
              'name': 'helmion-traefik',
              'namespace': 'router'}}

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
import pprint

from helmion.info import RepositoryInfo

repoinfo = RepositoryInfo('https://helm.traefik.io/traefik')

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

print('Chart values file')
print('===================')

# pprint.pprint(repoinfo.chartVersion('traefik', '9.10.1').getValuesFile())
print(repoinfo.chartVersion('traefik', '9.10.1').readArchiveFiles().archiveFiles['values.yaml'])

print('')

print('Chart file contents')
print('===================')
with repoinfo.chartVersion('traefik', '9.10.1').fileOpen() as tar_file:
    for fname in tar_file.getnames():
        print("- {}".format(fname))
```

Output:

```text
Repository charts
=================
Chart: traefik
Description: A Traefik based Kubernetes ingress controller
Latest: 9.10.1
	release: 9.10.1
	release: 9.10.0
	release: 9.9.0
	release: 9.8.4
	release: 9.8.3
	release: 9.8.2
	release: 9.8.1

<...more...>

Chart values file
===================
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
  # Additional pod annotations (e.g. for mesh injection or prometheus scraping)
  podAnnotations: {}

<...more...>

Chart file contents
===================
- traefik/Chart.yaml
- traefik/values.yaml
- traefik/templates/_helpers.tpl
- traefik/templates/dashboard-hook-ingressroute.yaml
- traefik/templates/deployment.yaml
- traefik/templates/hpa.yaml

<...more...>
```

### Credits

based on

Based on [MichaelVL/kubernetes-deploy-tools](https://github.com/MichaelVL/kubernetes-deploy-tools).

## Author

Rangel Reale (rangelreale@gmail.com)
