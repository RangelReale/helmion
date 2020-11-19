from typing import Any, Optional, Sequence, TypedDict, Callable

from jsonpatchext import JsonPatchExt

from .chart import Processor, Request
from .config import BoolFilter
from .data import ChartData
from .util import helm_hook_anno, is_namedspaced, parse_apiversion


class PatchType(TypedDict, total=False):
    condition: Any
    conditions: Sequence[Any]
    patch: Any
    patches: Sequence[Any]


FilterFunc = Callable[[Any], bool]


class DefaultProcessor(Processor):
    add_namespace: bool
    namespaced_filter: BoolFilter
    hook_filter: BoolFilter
    hook_filter_list: Optional[Sequence[str]]
    jsonpatches: Optional[Sequence[PatchType]]
    filterfunc: Optional[FilterFunc]

    def __init__(self, add_namespace: bool = False, namespaced_filter: BoolFilter = BoolFilter.ALL,
                 hook_filter: BoolFilter = BoolFilter.ALL, hook_filter_list: Optional[Sequence[str]] = None,
                 jsonpatches: Optional[Sequence[PatchType]] = None,
                 filterfunc: Optional[FilterFunc] = None):
        self.add_namespace = add_namespace
        self.namespaced_filter = namespaced_filter
        self.hook_filter = hook_filter
        self.hook_filter_list = hook_filter_list
        self.jsonpatches = jsonpatches
        self.filterfunc = filterfunc

    def filter(self, request: Request, data: ChartData) -> bool:
        if self.namespaced_filter != BoolFilter.ALL:
            is_ns = 'metadata' in data and 'namespace' in data['metadata']
            if is_ns != (self.namespaced_filter == BoolFilter.IF_TRUE):
                return False

        if self.hook_filter != BoolFilter.ALL:
            is_hook = False
            if 'metadata' in data and 'annotations' in data['metadata']:
                anno = data['metadata']['annotations']
                if anno and helm_hook_anno in anno:
                    if self.hook_filter_list is None or anno[helm_hook_anno] in self.hook_filter_list:
                        is_hook = True
            if is_hook != (self.hook_filter == BoolFilter.IF_TRUE):
                return False

        if self.filterfunc is not None:
            if not self.filterfunc(data):
                return False

        return True

    def mutateBefore(self, request: Request, data: ChartData) -> None:
        # Add namespace
        if self.add_namespace:
            apiVersion = data['apiVersion']
            kind = data['kind']
            if is_namedspaced(apiVersion, kind):
                if 'metadata' not in data:
                    data['metadata'] = {}
                if 'namespace' not in data['metadata']:
                    data['metadata']['namespace'] = request.namespace

    def mutate(self, request: Request, data: ChartData) -> None:
        def do_check(check):
            if callable(check):
                return check(data)
            else:
                return JsonPatchExt(check).check(data)

        if self.jsonpatches is not None:
            for jp in self.jsonpatches:
                if 'condition' in jp:
                    if not do_check(jp['condition']):
                        continue
                if 'conditions' in jp:
                    is_check = False
                    for check in jp['conditions']:
                        if do_check(check):
                            is_check = True
                            break
                    if not is_check:
                        continue
                if 'patch' in jp:
                    JsonPatchExt(jp['patch']).apply(data, in_place=True)
                if 'patches' in jp:
                    for patch in jp['patches']:
                        JsonPatchExt(patch).apply(data, in_place=True)


class FilterCRDs(Processor):
    def filter(self, request: Request, data: ChartData) -> bool:
        return parse_apiversion(data['apiVersion'])[0] == 'apiextensions.k8s.io' and data['kind'] == 'CustomResourceDefinition'


class FilterRemoveHelmData(Processor):
    only_exlcusive: bool
    remove_hooks: bool

    def __init__(self, only_exlcusive: bool = True, remove_hooks: bool = False):
        super().__init__()
        self.only_exlcusive = only_exlcusive
        self.remove_hooks = remove_hooks

    def mutate(self, request: Request, data: ChartData) -> None:
        labels_general = ['app.kubernetes.io/managed-by']
        annotations_general = []

        root_data = []
        if 'metadata' in data:
            root_data.append(data['metadata'])
        if parse_apiversion(data['apiVersion'])[0] == 'apps' and data['kind'] == 'Deployment':
            if 'spec' in data and 'template' in data['spec'] and 'metadata' in data['spec']['template']:
                root_data.append(data['spec']['template']['metadata'])

        for root in root_data:
            if 'labels' in root:
                if root['labels'] is not None:
                    for lname in list(root['labels'].keys()):
                        if lname.startswith('helm.sh/'):
                            del root['labels'][lname]
                        elif not self.only_exlcusive and lname in labels_general:
                            if lname != 'app.kubernetes.io/managed-by' or root['labels'][lname] == 'Helm':
                                del root['labels'][lname]
                if root['labels'] is None or len(root['labels']) == 0:
                    del root['labels']

            if 'annotations' in root:
                if root['annotations'] is not None:
                    for lname in list(root['annotations'].keys()):
                        if lname.startswith('helm.sh/'):
                            if self.remove_hooks or lname != 'helm.sh/hook':
                                del root['annotations'][lname]
                        elif not self.only_exlcusive and lname in annotations_general:
                            del root['annotations'][lname]
                if root['annotations'] is None or len(root['annotations']) == 0:
                    del root['annotations']