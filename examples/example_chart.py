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
