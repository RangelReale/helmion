import pprint

from helmion.info import RepositoryInfo

repository_url = 'https://helm.traefik.io/traefik'
chart_name = 'traefik'
chart_version = '9.10.1'
# chart_version = '<=9.9.*'

# repository_url = 'https://grafana.github.io/loki/charts'
# chart_name = 'loki-stack'
# chart_version = None

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

# pprint.pprint(repoinfo.mustChartVersion(chart_name, chart_version).getChartFile())
print(repoinfo.mustChartVersion(chart_name, chart_version).getArchiveFile('Chart.yaml'))


print('')
print('values.yaml')
print('===========')

# pprint.pprint(repoinfo.mustChartVersion(chart_name, chart_version).getValuesFile())
print(repoinfo.mustChartVersion(chart_name, chart_version).getArchiveFile('values.yaml'))


print('')
print('dependencies')
print('============')

pprint.pprint(repoinfo.mustChartVersion(chart_name, chart_version).getDependencies())


print('')
print('Chart file contents')
print('===================')
with repoinfo.mustChartVersion(chart_name, chart_version).fileOpen() as tar_file:
    for fname in tar_file.getnames():
        print("- {}".format(fname))
