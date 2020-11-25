import difflib

import yaml

from helmion.helmchart import HelmRequest
from helmion.info import RepositoryInfo

source_version = '9.8.4'
# new_version = '9.10.2'
new_version = None

helmreq = HelmRequest(repository='https://helm.traefik.io/traefik', chart='traefik', version=source_version,
                      releasename='helmion-traefik', namespace='router')

repoinfo = RepositoryInfo(helmreq.repository)
repochart = repoinfo.mustChart(helmreq.chart)
repochartversion = repoinfo.mustChartVersion(helmreq.chart, helmreq.version)
repochartnewversion = repoinfo.mustChartVersion(helmreq.chart, new_version)

print('$' * 40)
print('$$ Repository: {}'.format(repoinfo.url))
print('$$ Chart: {}'.format(repochart.name))
print('$$ Version: {}'.format(repochartversion.version))
print('$$ New Version: {}'.format(repochartnewversion.version))
if repochartversion.sources is not None:
    print('$$ Sources: {}'.format(', '.join(repochartversion.sources)))
print('$' * 40)
print()
print('Chart versions')
print('==============')
vct = 0
vfound = False
for r in repochart.versions:
    cur = ''
    if r.version == repochartversion.version:
        vfound = True
        cur = ' (SRC)'
    elif r.version == repochartnewversion.version:
        cur = ' (NEW)'

    print('\trelease: {}{}'.format(r.version, cur))
    vct += 1
    if (vfound and vct > 5) or vct > 15:
        break

if repochartversion.version != repochartnewversion.version:
    helmreqnew = helmreq.clone()
    helmreqnew.version = repochartnewversion.version

    print()
    print('$' * 40)
    print('$$ Values')
    print('$' * 40)
    for vfline in difflib.unified_diff(helmreq.allowedValuesRaw().splitlines(keepends=True),
                                       helmreqnew.allowedValuesRaw().splitlines(keepends=True),
                                       fromfile='before', tofile='after'):
        print(vfline, end='')

    print()
    print('$' * 40)
    print('$$ Templates')
    print('$' * 40)
    helmres = helmreq.generate()
    dump = yaml.dump_all(helmres.data, Dumper=yaml.Dumper, sort_keys=False)
    helmresnew = helmreqnew.generate()
    dumpnew = yaml.dump_all(helmresnew.data, Dumper=yaml.Dumper, sort_keys=False)
    for vfline in difflib.unified_diff(
        dump.splitlines(keepends=True), dumpnew.splitlines(keepends=True),
        fromfile='before', tofile='after'):
        print(vfline, end='')

else:
    print('Same version')
