import pprint

from jsonpatchext.mutators import InitItemMutator  # type: ignore

from helmion.chart import ProcessorChain, SplitterCategoryResult
from helmion.config import BoolFilter
from helmion.helmchart import HelmRequest
from helmion.processor import DefaultProcessor, FilterRemoveHelmData, FilterCRDs, DefaultSplitter, ProcessorSplitter

req = HelmRequest(repository='https://helm.traefik.io/traefik', chart='traefik', version='9.10.1',
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

res = req.generate().process(ProcessorChain(
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

mres = res.split(reqsplitter)

for category, category_chart in mres.items():
    print('')
    print('*** {} ***'.format(category))
    for d in category_chart.data:
        pprint.pprint(d)


# Split and filter by Kind

print('')
print('Split Deployment and ServiceAccount charts')
print('==========================================')

reqsplitter2 = DefaultSplitter(categoryfunc=lambda c, d: SplitterCategoryResult.categories('deployment') if d['kind'] == 'Deployment' else SplitterCategoryResult.categories('serviceaccount') if d['kind'] == 'ServiceAccount' else SplitterCategoryResult.NONE)

mres = res.split(reqsplitter2, ensure_categories=['deployment', 'serviceaccount'])

for category, category_chart in mres.items():
    print('')
    print('*** {} ***'.format(category))
    for d in category_chart.data:
        pprint.pprint(d)
