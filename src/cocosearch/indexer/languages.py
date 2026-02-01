"""Backward-compatible re-exports from cocosearch.handlers.

DEPRECATED: Import directly from cocosearch.handlers instead.
This module is retained for backward compatibility only.
"""

from cocosearch.handlers import get_custom_languages
from cocosearch.handlers.hcl import HclHandler
from cocosearch.handlers.dockerfile import DockerfileHandler
from cocosearch.handlers.bash import BashHandler

# Re-export individual language specs for backward compatibility
HCL_LANGUAGE = HclHandler.SEPARATOR_SPEC
DOCKERFILE_LANGUAGE = DockerfileHandler.SEPARATOR_SPEC
BASH_LANGUAGE = BashHandler.SEPARATOR_SPEC

# Re-export aggregated list
DEVOPS_CUSTOM_LANGUAGES = get_custom_languages()

__all__ = [
    "HCL_LANGUAGE",
    "DOCKERFILE_LANGUAGE",
    "BASH_LANGUAGE",
    "DEVOPS_CUSTOM_LANGUAGES",
]
