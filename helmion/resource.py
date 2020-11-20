from typing import Sequence, Tuple, Optional, TypedDict

from .data import ChartData
from .exception import ParamError
from .util import parse_apiversion


kubernetes_non_namespaced_resources: Sequence[Tuple[str, str]] = [
    ('', 'List'),
    ('', 'ComponentStatus'),
    ('', 'Namespace'),
    ('', 'Node'),
    ('', 'PersistentVolume'),
    ('admissionregistration.k8s.io', 'MutatingWebhookConfiguration'),
    ('admissionregistration.k8s.io', 'ValidatingWebhookConfiguration'),
    ('apiextensions.k8s.io', 'CustomResourceDefinition'),
    ('apiregistration.k8s.io', 'APIService'),
    ('authentication.k8s.io', 'TokenReview'),
    ('authorization.k8s.io', 'SelfSubjectAccessReview'),
    ('authorization.k8s.io', 'SelfSubjectRulesReview'),
    ('authorization.k8s.io', 'SubjectAccessReview'),
    ('certificates.k8s.io', 'CertificateSigningRequest'),
    ('metrics.k8s.io', 'NodeMetrics'),
    ('migration.k8s.io', 'StorageState'),
    ('migration.k8s.io', 'StorageVersionMigration'),
    ('node.k8s.io', 'RuntimeClass'),
    ('policy', 'PodSecurityPolicy'),
    ('rbac.authorization.k8s.io', 'ClusterRoleBinding'),
    ('rbac.authorization.k8s.io', 'ClusterRole'),
    ('scheduling.k8s.io', 'PriorityClass'),
    ('storage.k8s.io', 'CSIDriver'),
    ('storage.k8s.io', 'CSINode'),
    ('storage.k8s.io', 'StorageClass'),
    ('storage.k8s.io', 'VolumeAttachment'),
]
"""
List of non-namespaced Kubernetes resources.

Returned with ```kubectl api-resources --namespaced=false```.
"""

def is_namespaced(apiVersion: str, kind: str):
    """Checks whether the Kubernetes object is namespaced"""
    pversion = parse_apiversion(apiVersion)
    for nn in kubernetes_non_namespaced_resources:
        if pversion[0] == nn[0] and nn[1] == kind:
            return False
    return True


def is_resource(data: ChartData, apiVersionNS: Optional[str] = None, apiVersionName: Optional[str] = None,
                kind: Optional[str] = None) -> bool:
    """
    Check if data is a resource of this type.

    :param data: chart data
    :param apiVersionNS: apiVersion namespace field
    :param apiVersionName: apiVersion name field
    :param kind: kind field
    :return: whether the data matches the filter fields
    :raises ParamError: on parameter error
    """
    if apiVersionNS is None and apiVersionName is None and kind is None:
        raise ParamError('At least one parameter must be set')
    pversion = parse_apiversion(data['apiVersion'])
    if apiVersionNS is not None and apiVersionNS != pversion[0]:
        return False
    if apiVersionName is not None and apiVersionName != pversion[1]:
        return False
    if kind is not None and kind != data['kind']:
        return False
    return True


class ResourceCheck(TypedDict, total=False):
    """
    Typed dict to check for resources.
    """
    apiVersionNS: str
    apiVersionName: str
    kind: str


def is_any_resource(data: ChartData, *resources: ResourceCheck) -> bool:
    """
    Check if data is any of the list of resources.

    :param data: chart data
    :param resources: list of resource checks
    :return: whether the data is any of the resources (OR)
    """
    for resource in resources:
        if is_resource(data, **resource):
            return True
    return False


def is_all_resources(data: ChartData, *resources: ResourceCheck) -> bool:
    """
    Check if data is all of the list of resources.

    :param data: chart data
    :param resources: list of resource checks
    :return: whether the data is all of the resources (AND)
    """
    for resource in resources:
        if not is_resource(data, **resource):
            return False
    return True


def is_list_resource(data: ChartData) -> bool:
    """
    Check if Kubernetes object is special ```kind: List```
    See `Any official docs around Kind: List? <https://github.com/kubernetes/kubectl/issues/837>`_
    """
    return is_resource(data, apiVersionNS='', kind='List')
