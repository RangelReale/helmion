from typing import Sequence, Tuple
from urllib.parse import urlparse


def remove_prefix(text, prefix):
    """Remove text prefix"""
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def is_absolute(url):
    """Checks whether the url is absolute"""
    return bool(urlparse(url).netloc)


def parse_apiversion(apiversion: str) -> Tuple[str, str]:
    """Parse ```apiVersion``` into a 2-item tuple."""
    p = apiversion.split('/', 1)
    if len(p) == 1:
        return '', p[0]
    return p[0], p[1]


helm_hook_anno = 'helm.sh/hook'


# kubectl api-resources --namespaced=false
kubernetes_non_namespaced_objects: Sequence[Tuple[str, str]] = [
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


def is_namedspaced(apiVersion: str, kind: str):
    """Checks whether the Kubernetes object is namespaced"""
    pversion = parse_apiversion(apiVersion)
    for nn in kubernetes_non_namespaced_objects:
        if pversion[0] == nn[0] and nn[1] == kind:
            return False
    return True


def is_list_resource(apiVersion: str, kind: str) -> bool:
    """
    Check if Kubernetes object is special ```kind: List```
    `Any official docs around Kind: List? <https://github.com/kubernetes/kubectl/issues/837>`_
    """
    pversion = parse_apiversion(apiVersion)
    return pversion[0] == '' and kind == 'List'
