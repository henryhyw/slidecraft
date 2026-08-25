"""Slidecraft public package API."""

from .agent import call_capability, list_capabilities, safe_call_capability
from .runtime.artifacts import ArtifactWorkspace
from .semantic_mapping.compiler import SemanticMapCompiler, compile_semantic_map

__all__ = [
    "ArtifactWorkspace",
    "SemanticMapCompiler",
    "call_capability",
    "compile_semantic_map",
    "list_capabilities",
    "safe_call_capability",
]
__version__ = "0.1.0a1"
