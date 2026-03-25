"""Workflow template loader."""

import os
import yaml
from typing import Optional

from .config import WORKFLOW_REGISTRY_PATH, DEFAULT_WORKFLOW


class WorkflowLoader:
    """Loads and validates workflow templates."""

    def __init__(self, registry_path: str = WORKFLOW_REGISTRY_PATH):
        self.registry_path = registry_path

    def load(self, name: str) -> dict:
        """Load a workflow template by name."""
        path = os.path.join(self.registry_path, f"{name}.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Workflow not found: {name}")
        with open(path) as f:
            spec = yaml.safe_load(f)
        self._validate(spec)
        return spec

    def list(self) -> list[str]:
        """List all available workflow templates."""
        if not os.path.exists(self.registry_path):
            return []
        return [
            f[:-5] for f in os.listdir(self.registry_path)
            if f.endswith(".yaml")
        ]

    def _validate(self, spec: dict) -> None:
        """Validate workflow schema."""
        required = ["name", "version", "stages"]
        for field in required:
            if field not in spec:
                raise ValueError(f"Missing required field: {field}")
        if not spec["stages"]:
            raise ValueError("Workflow must have at least one stage")


def load_workflow(name: str = DEFAULT_WORKFLOW) -> dict:
    """Convenience function to load a workflow."""
    loader = WorkflowLoader()
    return loader.load(name)
