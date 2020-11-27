import copy
import os
import subprocess
import tempfile
from typing import Optional, Mapping, Any, Sequence

from helmion.chart import Chart
from helmion.config import Config
from helmion.data import ChartData
from helmion.exception import ConfigurationError, ParamError, HelmError
from helmion.info import RepositoryInfo


class HelmConfig(Config):
    """
    Helm configuration.

    :param helm_bin: path of the ```helm``` executable
    :param kube_version: Kubernetes version used as ```Capabilities.KubeVersion.Major/Minor```
    :param api_versions: Kubernetes api versions used for ```Capabilities.APIVersions```
    :param sort_objects: whether to sort Kubernetes objects returned from Helm
    :param include_crds: whether to include crds from Helm
    """
    helm_bin: str
    helm_debug: bool
    kube_version: Optional[str]
    api_versions: Optional[Sequence[str]]
    include_crds: bool

    def __init__(self, helm_bin: str = 'helm', helm_debug: bool = False, kube_version: Optional[str] = None,
                 api_versions: Optional[Sequence[str]] = None, include_crds: bool = True, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.helm_bin = helm_bin
        self.helm_debug = helm_debug
        self.kube_version = kube_version
        self.api_versions = api_versions
        self.include_crds = include_crds


class HelmRequest:
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
    config: HelmConfig
    chart: str
    version: Optional[str]
    releasename: str
    repository: Optional[str]
    namespace: Optional[str]
    sets: Optional[Mapping[str, str]]
    values: Optional[Mapping[str, Any]]
    _allowedvalues: Optional[Mapping[str, Any]]
    _allowedvalueswithdeps: Optional[Mapping[str, Any]]

    def __init__(self, chart: str, version: Optional[str] = None, repository: Optional[str] = None, releasename: Optional[str] = None,
                 namespace: Optional[str] = None, sets: Optional[Mapping[str, str]] = None,
                 values: Optional[Mapping[str, Any]] = None, config: Optional[HelmConfig] = None):
        self.config = config if config is not None else HelmConfig()
        self.repository = repository
        self.chart = chart
        self.version = version
        self.releasename = releasename if releasename is not None else chart
        self.namespace = namespace
        self.sets = sets
        self.values = values
        self._allowedvalues = None
        self._allowedvalueswithdeps = None

    def clone(self):
        """
        Clone the current Helm request.

        :return: a clone of the current request
        """
        return HelmRequest(chart=self.chart, version=self.version, repository=self.repository, releasename=self.releasename,
                          namespace=self.namespace, sets=copy.deepcopy(self.sets), values=copy.deepcopy(self.values),
                          config=self.config)

    def allowedValues(self, forcedownload: bool = False) -> Mapping[str, Any]:
        """
        Returns the parsed ```values.yaml``` from the chart. It is download from the Internet on first access.

        :param forcedownload: whether to force download even if already cached in memory.
        :return: a :class:`Mapping` of the ```values.yaml``` for the chart.
        """
        if self.repository is None:
            raise ConfigurationError('Repository must be set to use this method')
        if not forcedownload and self._allowedvalues is not None:
            return self._allowedvalues
        chartversion = RepositoryInfo(url=self.repository, config=self.config).chartVersion(
            self.chart, self.version)
        if chartversion is None:
            raise ParamError('Chart version not found')
        self._allowedvalues = chartversion.getValuesFile()
        return self._allowedvalues

    def allowedValuesWithDependencies(self, forcedownload: bool = False) -> Mapping[str, Any]:
        """
        Returns the parsed ```values.yaml``` from the chart merged with each dependency ones.
        It is download from the Internet on first access.

        :param forcedownload: whether to force download even if already cached in memory.
        :return: a :class:`Mapping` of the ```values.yaml``` for the chart merged with each dependency.
        """
        if self.repository is None:
            raise ConfigurationError('Repository must be set to use this method')
        if not forcedownload and self._allowedvalueswithdeps is not None:
            return self._allowedvalueswithdeps
        chartversion = RepositoryInfo(url=self.repository, config=self.config).chartVersion(
            self.chart, self.version)
        if chartversion is None:
            raise ParamError('Chart version not found')
        self._allowedvalueswithdeps = chartversion.getValuesFileWithDependencies()
        return self._allowedvalueswithdeps

    def allowedValuesRaw(self) -> str:
        """
        Returns the raw ```values.yaml``` from the chart. It is download from the Internet.

        :return: the contents of the ```values.yaml``` for the chart.
        """
        if self.repository is None:
            raise ConfigurationError('Repository must be set to use this method')
        chartversion = RepositoryInfo(url=self.repository, config=self.config).chartVersion(
            self.chart, self.version)
        if chartversion is None:
            raise ParamError('Chart version not found')
        return chartversion.getArchiveFile('values.yaml')

    def generate(self) -> 'Chart':
        """
        Call Helm and generate the chart object templates.

        :param processor: processor to apply to returned object templates.
        :return: a :class:`Chart` instance containing the chart generated templates.
        :raises HelmError: on helm command errors
        :raises InputOutputError: on IO error
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = '{} template {} {}'.format(
                self.config.helm_bin, self.releasename, self.chart)
            if self.config.helm_debug:
                cmd += ' --debug'
            if self.config.include_crds:
                cmd += ' --include-crds'
            if self.repository is not None:
                cmd += ' --repo {}'.format(self.repository)
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
                    vfn_dst.write(self.config.yaml_dump(self.values))
                cmd += ' --values {}'.format(values_file)

            try:
                runcmd = subprocess.run(cmd, shell=True, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                serr = e.stderr.decode('utf-8')
                sout = e.stdout.decode('utf-8')
                raise HelmError("Error executing helm: {}".format(serr), cmd=cmd,
                                stdout=sout, stderr=serr) from e
            out = runcmd.stdout.decode('UTF-8','ignore')
            data: ChartData = self.config.yaml_load_all(out)

            ret = HelmChart(request=self, config=self.config)
            for d in data:
                if d is None:
                    continue
                if not isinstance(d, Mapping):
                    raise HelmError('Unknown data type in Helm template output: "{}"', repr(d))
                ret.data.append(d)

            return ret


class HelmChart(Chart):
    """
    HelmChart represents a set of object Kubernetes generated from a Helm chart.

    :param request: Chart request
    """
    request: HelmRequest

    def __init__(self, request: HelmRequest, config: Optional[Config] = None, data: Optional[Sequence[ChartData]] = None):
        super().__init__(config=config, data=data)
        self.request = request

    def createClone(self) -> 'Chart':
        return HelmChart(request=self.request, config=self.config)
