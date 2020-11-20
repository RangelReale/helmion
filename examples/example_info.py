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
print('Chart.yaml')
print('==========')

# pprint.pprint(repoinfo.chartVersion('traefik', '9.10.1').getChartFile())
print(repoinfo.chartVersion('traefik', '9.10.1').readArchiveFiles().archiveFiles['Chart.yaml'])


print('')
print('values.yaml')
print('===========')

# pprint.pprint(repoinfo.chartVersion('traefik', '9.10.1').getValuesFile())
print(repoinfo.chartVersion('traefik', '9.10.1').readArchiveFiles().archiveFiles['values.yaml'])


print('')
print('Chart file contents')
print('===================')
with repoinfo.chartVersion('traefik', '9.10.1').fileOpen() as tar_file:
    for fname in tar_file.getnames():
        print("- {}".format(fname))
