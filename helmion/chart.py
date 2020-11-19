import copy
import os
import subprocess
import tempfile
from typing import Optional, Mapping, Any, List, Sequence, Union, Callable, Dict

import yaml

from .config import Config
from .data import ChartData
from .exception import HelmError, InputOutputError, ConfigurationError
from .info import RepositoryInfo
from .util import is_list_resource


class Processor:
    """
    Processor filters and mutates charts and its objects.
    """
    def filter(self, request: 'Request', data: ChartData) -> bool:
        """
        Filters chart objects.

        :param request: original chart request
        :param data: chart object data
        :return: True to include the object, False to exclude it
        """
        return True

    def mutateBefore(self, request: 'Request', data: ChartData) -> None:
        """
        Mutate chart object before filtering.

        :param request: original chart request
        :param data: chart object data
        """
        pass

    def mutate(self, request: 'Request', data: ChartData) -> None:
        """
        Mutate chart object after filtering.

        :param request: original chart request
        :param data: chart object data
        """
        pass

    def mutateComplete(self, request: 'Request', data: Sequence[ChartData]) -> Optional[Sequence[ChartData]]:
        """
        Mutate complete chart objects after all other processing.

        :param request: original chart request
        :param data: list of chart object data
        :returns: if not None, replaces the complete chart object data with the result, otherwise keep
            the current value.
        """
        return None


class ProcessorChain(Processor):
    """
    A processor for chaining multiple :class:`Processor`.

    :param processor: list of :class:`Processor`.
    """
    processors: Sequence[Processor]

    def __init__(self, *processor: Processor):
        self.processors = processor

    def filter(self, request: 'Request', data: ChartData) -> bool:
        for p in self.processors:
            if not p.filter(request, data):
                return False
        return True

    def mutateBefore(self, request: 'Request', data: ChartData) -> None:
        for p in self.processors:
            p.mutateBefore(request, data)

    def mutate(self, request: 'Request', data: ChartData) -> None:
        for p in self.processors:
            p.mutate(request, data)

    def mutateComplete(self, request: 'Request', data: Sequence[ChartData]) -> Optional[Sequence[ChartData]]:
        lastdata = data
        for p in self.processors:
            pret = p.mutateComplete(request, lastdata)
            if pret is not None:
                lastdata = pret
        return lastdata


class Request:
    """
    A chart template request.

    :param repository: Helm repository url
    :param chart: chart name
    :param releasename: a release name. If None, will use value of ```chart```
    :param namespace: target Kubernetes namespace. If None, no namespace will be sent to Helm
    :param sets: Helm ```--set``` parameters
    :param values: Values to be sent to Helm ```--values``` parameter
    :param config: configuration
    """
    config: Config
    repository: str
    chart: str
    version: str
    releasename: str
    namespace: Optional[str]
    sets: Optional[Mapping[str, str]]
    values: Optional[Mapping[str, Any]]
    _allowedvalues: Optional[Mapping[str, Any]]

    def __init__(self, repository: str, chart: str, version: str, releasename: Optional[str] = None,
                 namespace: Optional[str] = None, sets: Optional[Mapping[str, str]] = None,
                 values: Optional[Mapping[str, Any]] = None, config: Optional[Config] = None):
        self.config = config if config is not None else Config()
        self.repository = repository
        self.chart = chart
        self.version = version
        self.releasename = releasename if releasename is not None else chart
        self.namespace = namespace
        self.sets = sets
        self.values = values
        self._allowedvalues = None

    def allowedValues(self, forcedownload: bool = False) -> Mapping[str, Any]:
        """
        Returns the parsed ```values.yaml``` from the chart. It is download from the Internet on first access.

        :param forcedownload: whether to force download even if already cached in memory.
        :return: a :class:`Mapping` of the ```values.yaml``` for the chart.
        """
        if not forcedownload and self._allowedvalues is not None:
            return self._allowedvalues
        self._allowedvalues = RepositoryInfo(url=self.repository, config=self.config).chartVersion(
            self.chart, self.version).getValuesFile()
        return self._allowedvalues

    def generate(self, processor: Optional[Processor] = None) -> 'Chart':
        """
        Call Helm and generate the chart object templates.

        :param processor: processor to apply to returned object templates.
        :return: a :class:`Chart` instance containing the chart generated templates.
        :raises HelmError: on helm command errors
        :raises InputOutputError: on IO error
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = '{} template {} {} --repo {} --include-crds'.format(
                self.config.helm_bin, self.releasename, self.chart, self.repository)
            if self.namespace is not None:
                cmd += ' --namespace {}'.format(self.namespace)
            if self.version is not None:
                cmd += ' --version {}'.format(self.version)
            if self.config.kube_version is not None:
                cmd += ' --kube-version {}'.format(self.config.kube_version)
            if self.config.api_versions is not None:
                for apiver in self.config.api_versions:
                    cmd += ' --api-versions {}'.format(apiver)

            if self.sets is not None:
                for k,v in self.sets.items():
                    cmd += " --set {}='{}'".format(k, v)

            if self.values is not None:
                values_file = os.path.join(tmpdir, 'values.yaml')
                with open(values_file, 'w') as vfn_dst:
                    vfn_dst.write(yaml.dump(self.values, Dumper=yaml.Dumper, sort_keys=False))
                cmd += ' --values {}'.format(values_file)

            try:
                runcmd = subprocess.run(cmd, shell=True, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                raise HelmError("Error executing helm: {}".format(e.stderr.decode('utf-8')), cmd=cmd) from e
            out = runcmd.stdout.decode('UTF-8','ignore')
            try:
                data = yaml.load_all(out, Loader=yaml.SafeLoader)
            except yaml.YAMLError as e:
                raise InputOutputError(str(e)) from e

            ret = Chart(self)
            for d in data:
                ret.data.append(d)

        return self.postprocess(ret.process(processor))

    def postprocess(self, chart: 'Chart') -> 'Chart':
        """
        Postprocess the chart.

        :param chart: chart to postprocess
        :return: the postprocessed chart
        """
        if self.config.sort:
            chart.sort()
        return chart


SplitterCategoryFuncResult = Optional[Union[bool, str, List[str]]]
"""
The :class:`Splitter` categorization function.

The possible return types are:

- ```bool```: True includes the object in ALL categories, False in none
- ```str```: includes the object only in this category
- ```List[str]```: includes the object in the list of categories
"""


class Splitter:
    """
    Chart splitter configuration.

    This splits chart objects in different categories using functions and filters.

    It is possible for a chart object to appear in more than one category, depending on the
    splitter configuration.

    :param categories: a ```Mapping``` of category names and optional processor.
    :param categoryfunc: a function to choose categories for the chart objects. See
        :data:`SplitterCategoryFuncResult` for details.
    """
    categories: Mapping[str, Optional[Processor]]
    categoryfunc: Optional[Callable[[Any], SplitterCategoryFuncResult]]

    def __init__(self, categories: Mapping[str, Optional[Processor]],
                 categoryfunc: Optional[Callable[[Any], SplitterCategoryFuncResult]] = None):
        self.categories = categories
        self.categoryfunc = categoryfunc

    def category(self, data: ChartData) -> SplitterCategoryFuncResult:
        """
        Returns the categories that the chart object should be added to.

        :param data: chart data
        :return: splitter category result. See  :data:`SplitterCategoryFuncResult` for details.
        """
        if self.categoryfunc is not None:
            return self.categoryfunc(data)
        return True


class Chart:
    """
    Chart represents a set of object Kubernetes generated from a Helm chart.

    :param request: Chart request
    """
    request: Request
    data: List[ChartData]
    """List of objected generated from the Helm chart"""

    def __init__(self, request: Request, data: Optional[Sequence[ChartData]] = None):
        self.request = request
        self.data = []
        if data is not None:
            self.data.extend(data)

    def clone(self) -> 'Chart':
        """
        Clones the current chart.

        :return: a clone of the current :class:`Chart` class
        """
        ret = Chart(self.request)
        ret.data = copy.deepcopy(self.data)
        return ret

    def process(self, processor: Optional[Processor]) -> 'Chart':
        """
        Process the current chart using the processor and return a new :class:`Chart` instance if
        a processor was passed, otherwise returns the same instance.

        The source :class:`Chart` remains unchanged in case of processing.

        :param processor: the :class:`Processor` to apply. If None, returns the same instance unchanged.
        :return: a processed :class:`Chart` instance, or the same instance if *processor* is None.
        """
        if processor is None:
            return self

        ret = Chart(self.request)
        for d in self.data:
            newd = copy.deepcopy(d)
            if self.request.config.parse_list_resource and is_list_resource(newd['apiVersion'], newd['kind']):
                # https://github.com/kubernetes/kubectl/issues/837
                newditems: List[ChartData] = []
                if 'items' in newd:
                    for newditem in newd['items']:
                        processor.mutateBefore(self.request, newditem)
                        if not processor.filter(self.request, newditem):
                            continue
                        processor.mutate(self.request, newditem)
                        newditems.append(newditem)
                if len(newditems) == 0:
                    continue
                newd['items'] = newditems
            else:
                processor.mutateBefore(self.request, newd)
                if not processor.filter(self.request, newd):
                    continue
                processor.mutate(self.request, newd)
            ret.data.append(newd)

        newdata = processor.mutateComplete(self.request, ret.data)
        if newdata is not None:
            ret.data = newdata

        return ret

    def split(self, splitter: Splitter) -> Mapping[str, 'Chart']:
        """
        Splits the chart objects in a list of categories.

        Returns new :class:`Chart` instances, the source :class:`Chart` remains unchanged.

        :param splitter: the splitter to use to categorize the objects.
        :return: a ```Mapping``` of categories and their charts
        :raises ConfigurationError: on a category that not exists
        """
        ret: Dict[str, 'Chart'] = {}

        for cname in splitter.categories.keys():
            ret[cname] = Chart(self.request)

        for d in self.data:
            category = splitter.category(d)
            categorylist = None
            if category is True:
                categorylist = list(splitter.categories.keys())
            elif isinstance(category, str):
                categorylist = [category]
            elif isinstance(category, Sequence):
                categorylist = category

            if categorylist is not None:
                for cname in categorylist:
                    if cname not in splitter.categories.keys():
                        raise ConfigurationError('Unknown category: {}'.format(cname))
                    ret[cname].data.append(copy.deepcopy(d))

        for cname, cprocessor in splitter.categories.items():
            if cprocessor is not None:
                ret[cname] = ret[cname].process(cprocessor)

        return ret

    def sort(self):
        """
        Sort resource list by resource name, but without changing overall resource kind sorting
        """
        out = []
        tmp = []
        last_kind = None
        for r in self.data:
            kind = r['kind']
            if last_kind and kind != last_kind:
                out += sorted(tmp, key=lambda r: r['metadata']['name'])
                tmp = []
            tmp.append(r)
            last_kind = kind
        out += sorted(tmp, key=lambda r: r['metadata']['name'])
        self.data = out
