from typing import Any, Optional, Sequence, TypedDict, Callable, Mapping, List, Union

from jsonpatchext import JsonPatchExt  # type: ignore

from .chart import Processor, Splitter, SplitterCategoryFuncResult, SplitterCategoryResultWrap, Chart, \
    SplitterCategoryResult
from .config import BoolFilter
from .data import ChartData
from .exception import ParamError
from .helmchart import HelmChart
from .resource import is_namespaced
from .util import helm_hook_anno, parse_apiversion


class PatchType(TypedDict, total=False):
    """
    A helper for applying :mod:`jsonpatchext`.
    """
    condition: Any
    """A single :mod:`jsonpatchext` condition to apply this patch"""

    conditions: Sequence[Any]
    """Multiple :mod:`jsonpatchext` conditions to apply this patch. Only one of the condition must match. (OR match)."""

    patch: Any
    """A single :mod:`jsonpatchext` to apply."""

    patches: Sequence[Any]
    """Multiple :mod:`jsonpatchext` to apply, in order."""


FilterFunc = Callable[[ChartData], bool]
"""
A filter function that takes a chart object data and returns whether to include (True) or not (False).
"""


class DefaultProcessor(Processor):
    """
    A default processor for common filters.

    :param add_namespace: if True or str, sets the namespace to all namespaced Kubernetes objects
        if not already set. ```True``` is only available for Helm charts, since it contains a "namespace" property.
    :param namespaced_filter: If ```BoolFilter.IF_TRUE``` includes only objects containing a "metadata.namespace"
        property. If ```BoolFilter.IF_FALSE```, includes only objects NOT containing a "metadata.namespace"
        property. If ```BoolFilter.ALL```, don't filter namespaces.
    :param hook_filter: If ```BoolFilter.IF_TRUE``` includes only objects containing a Helm hook. If
        ```BoolFilter.IF_FALSE```, includes only objects NOT containing a Helm hook. If ```BoolFilter.ALL```,
        don't filter by present of Helm hooks.
    :param hook_filter_list: a list of hooks to filter if filtering hooks. If None, includes all hooks.
    :param jsonpatches: :mod:`jsonpatchext` patches to apply. See :data:`PatchType`.
    :param filterfunc: a callable to call on each object to check for inclusion.
    """
    add_namespace: Union[str, bool]
    namespaced_filter: BoolFilter
    hook_filter: BoolFilter
    hook_filter_list: Optional[Sequence[str]]
    jsonpatches: Optional[Sequence[PatchType]]
    filterfunc: Optional[FilterFunc]

    def __init__(self, add_namespace: Union[str, bool] = False, namespaced_filter: BoolFilter = BoolFilter.ALL,
                 hook_filter: BoolFilter = BoolFilter.ALL, hook_filter_list: Optional[Sequence[str]] = None,
                 jsonpatches: Optional[Sequence[PatchType]] = None,
                 filterfunc: Optional[FilterFunc] = None):
        self.add_namespace = add_namespace
        self.namespaced_filter = namespaced_filter
        self.hook_filter = hook_filter
        self.hook_filter_list = hook_filter_list
        self.jsonpatches = jsonpatches
        self.filterfunc = filterfunc

    def filter(self, chart: Chart, data: ChartData) -> bool:
        if self.namespaced_filter != BoolFilter.ALL:
            is_ns = 'metadata' in data and 'namespace' in data['metadata']
            if is_ns != (self.namespaced_filter == BoolFilter.IF_TRUE):
                return False

        if self.hook_filter != BoolFilter.ALL:
            is_hook = False
            if 'metadata' in data and 'annotations' in data['metadata']:
                anno = data['metadata']['annotations']
                if anno and helm_hook_anno in anno:
                    helm_hooks = anno[helm_hook_anno].split(',')
                    if self.hook_filter_list is None or set(self.hook_filter_list).issubset(set(helm_hooks)):
                        is_hook = True
            if is_hook != (self.hook_filter == BoolFilter.IF_TRUE):
                return False

        if self.filterfunc is not None:
            if not self.filterfunc(data):
                return False

        return True

    def mutateBefore(self, chart: Chart, data: ChartData) -> None:
        # Add namespace
        if self.add_namespace is not False:
            apiVersion = data['apiVersion']
            kind = data['kind']
            if is_namespaced(apiVersion, kind):
                if 'metadata' not in data:
                    data['metadata'] = {}
                if 'namespace' not in data['metadata']:
                    namespace = self.add_namespace
                    if namespace is True:
                        if not isinstance(chart, HelmChart):
                            raise ParamError('Automatic namespace name is only available for Helm charts')
                        namespace = chart.request.namespace
                    data['metadata']['namespace'] = namespace

    def mutate(self, chart: Chart, data: ChartData) -> None:
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
    """
    Filter charts that are CRDs (```apiVersion: apiextensions.k8s.io/CustomResourceDefinition```).

    :param invert_filter: if True, filters charts the are NOT CRDs.
    """
    invert_filter: bool

    def __init__(self, invert_filter: bool = False):
        super().__init__()
        self.invert_filter = invert_filter

    def filter(self, chart: Chart, data: ChartData) -> bool:
        value = parse_apiversion(data['apiVersion'])[0] == 'apiextensions.k8s.io' and data['kind'] == 'CustomResourceDefinition'
        return value != self.invert_filter


class FilterRemoveHelmData(Processor):
    """
    Removes data added by Helm.

    :param only_exlcusive: if True, only remove items using the ```helm.sh``` parameter namespace, otherwise remove
        all items that are detected to be added by Helm.
    :param remove_hooks: whether to also remove hooks, as they are also on the ```helm.sh``` parameter namespace.
    :param remove_managedby: whether to remove app.kubernetes.io/managed-by: Helm.
    """
    only_exlcusive: bool
    remove_hooks: bool
    remove_managedby: bool

    def __init__(self, only_exlcusive: bool = True, remove_hooks: bool = False, remove_managedby: bool = True):
        super().__init__()
        self.only_exlcusive = only_exlcusive
        self.remove_hooks = remove_hooks
        self.remove_managedby = remove_managedby

    def mutate(self, chart: Chart, data: ChartData) -> None:
        """
        Removes Helm data.

        If label *app.kubernetes.io/managed-by == Helm*, it is also removed.

        :param chart:
        :param data:
        :return:
        """
        labels_general: Sequence[str] = ['app.kubernetes.io/managed-by']
        annotations_general: Sequence[str] = []

        root_data = []
        # Locate all sources of metadata
        if 'metadata' in data:
            root_data.append(data['metadata'])
        if parse_apiversion(data['apiVersion'])[0] == 'apps' and data['kind'] in ['Deployment',
            'StatefulSet', 'DaemonSet', 'ReplicaSet']:
            # Check metadata of objects that have a spec.template
            if 'spec' in data and 'template' in data['spec'] and 'metadata' in data['spec']['template']:
                root_data.append(data['spec']['template']['metadata'])

        for root in root_data:
            if 'labels' in root:
                # Remove labels
                if root['labels'] is not None:
                    for lname in list(root['labels'].keys()):
                        if lname.startswith('helm.sh/'):
                            del root['labels'][lname]
                        elif self.remove_managedby and lname == 'app.kubernetes.io/managed-by' and \
                                root['labels'][lname] == 'Helm':
                            del root['labels'][lname]
                        elif lname == 'heritage' and root['labels'][lname] == 'Helm':
                            del root['labels'][lname]
                        elif not self.only_exlcusive and lname in labels_general:
                            del root['labels'][lname]
                if root['labels'] is None or len(root['labels']) == 0:
                    del root['labels']

            if 'annotations' in root:
                # Remove annotations
                if root['annotations'] is not None:
                    for lname in list(root['annotations'].keys()):
                        if lname.startswith('helm.sh/'):
                            if self.remove_hooks or not lname.startswith('helm.sh/hook'):
                                del root['annotations'][lname]
                        elif not self.only_exlcusive and lname in annotations_general:
                            del root['annotations'][lname]
                if root['annotations'] is None or len(root['annotations']) == 0:
                    del root['annotations']


class DefaultSplitter(Splitter):
    """
    Default chart splitter configuration.

    This splits chart objects in different categories using a functions.

    :param categoryfunc: a function to choose categories for the chart objects. See
        :data:`SplitterCategoryFuncResult` for details.
    """
    _categoryfunc: Callable[[Chart, ChartData], SplitterCategoryFuncResult]
    _categories: Optional[Sequence[str]]
    _default_categories: Optional[Sequence[str]]

    def __init__(self, categoryfunc: Callable[[Chart, ChartData], SplitterCategoryFuncResult],
                 categories: Optional[Sequence[str]] = None, default_categories: Optional[Sequence[str]] = None):
        self._categoryfunc = categoryfunc  # type: ignore
        self._categories = categories
        self._default_categories = default_categories

    def category(self, chart: Chart, data: ChartData) -> SplitterCategoryFuncResult:
        ret = self._categoryfunc(chart, data)  # type: ignore
        if ret == SplitterCategoryResult.NONE and self._default_categories is not None:
            return SplitterCategoryResult.categories(self._default_categories)
        return ret

    def category_list(self) -> Optional[Sequence[str]]:
        return self._categories


class ListSplitter(Splitter):
    """
    Chart splitter using a list of callables

    :param categories: a ```Mapping``` of category names and callables.
        The callable receive these parameters:

        - category name
        - chart request :class:`Request`
        - chart data :class:`ChartData`
    :param require_all: require that all chart data are returned in at least one category
    :param exactly_one_category: require all that to be returned to exactly one category
    """
    categories: Mapping[str, Callable[[str, Chart, ChartData], bool]]
    require_all: bool
    exactly_one_category: bool
    default_categories: Optional[Sequence[str]]

    def __init__(self, categories: Mapping[str, Callable[[str, Chart, ChartData], bool]], require_all: bool = False,
                 exactly_one_category: bool = False, default_categories: Optional[Sequence[str]] = None):
        self.categories = categories
        self.require_all = require_all
        self.exactly_one_category = exactly_one_category
        self.default_categories = default_categories

    def category(self, chart: Chart, data: ChartData) -> SplitterCategoryFuncResult:
        ret: List[str] = []
        for cname, cvalue in self.categories.items():
            if cvalue(cname, chart, data):
                ret.append(cname)
        if len(ret) == 0 and self.require_all:
            raise ParamError('All data area required to have categories, but "{}" have none'.format(repr(data)))
        if self.exactly_one_category and len(ret) != 1:
            raise ParamError('All data area must have exactly one category, but "{}" have {}'.format(repr(data), len(ret)))
        if len(ret) == 0 and self.default_categories is not None:
            return SplitterCategoryResult.categories(self.default_categories)
        return SplitterCategoryResultWrap(ret)

    def category_list(self) -> Optional[Sequence[str]]:
        return list(self.categories.keys())


class ProcessorSplitter(Splitter):
    """
    Chart splitter using a processor "filter" method.

    :param processors: a ```Mapping``` of category names and processors.
    :param require_all: require that all chart data are returned in at least one category
    :param exactly_one_category: require all that to be returned to exactly one category
    """
    processors: Mapping[str, Processor]
    require_all: bool
    exactly_one_category: bool
    default_categories: Optional[Sequence[str]]

    def __init__(self, processors: Mapping[str, Processor], require_all: bool = False,
                 exactly_one_category: bool = False, default_categories: Optional[Sequence[str]] = None):
        self.processors = processors
        self.require_all = require_all
        self.exactly_one_category = exactly_one_category
        self.default_categories = default_categories

    def category(self, chart: Chart, data: ChartData) -> SplitterCategoryFuncResult:
        ret: List[str] = []
        for cname, cvalue  in self.processors.items():
            if cvalue.filter(chart, data):
                ret.append(cname)
        if len(ret) == 0 and self.require_all:
            raise ParamError('All data area required to have categories, but "{}" have none'.format(repr(data)))
        if self.exactly_one_category and len(ret) != 1:
            raise ParamError('All data area must have exactly one category, but "{}" have {}'.format(repr(data), len(ret)))
        if len(ret) == 0 and self.default_categories is not None:
            return SplitterCategoryResult.categories(self.default_categories)
        return SplitterCategoryResultWrap(ret)

    def category_list(self) -> Optional[Sequence[str]]:
        return list(self.processors.keys())
