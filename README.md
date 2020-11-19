# Helmion

[![PyPI version](https://img.shields.io/pypi/v/helmion.svg)](https://pypi.python.org/pypi/helmion/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/helmion.svg)](https://pypi.python.org/pypi/helmion/)

Helmion is a python library to download and customize [Helm](https://helm.sh/) charts.

* Website: https://github.com/RangelReale/helmion
* Repository: https://github.com/RangelReale/helmion.git
* Documentation: https://helmion.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/helmion

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
