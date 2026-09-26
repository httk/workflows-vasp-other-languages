"""Each packaged workflow directory: loads, matches its own runner, and is complete.

Adapted from workflows-vasp's ``tests/test_packages.py``. A compiled package's
command runs its build artifact, so its ``--describe`` check builds a copy
first and is skipped when that package's toolchain is missing.
"""

import json
from pathlib import Path

import pytest
from httk.core.plugins.manifest import parse_plugin_manifest
from httk.workflow.packages import load_workflow_package

from conftest import REPO_ROOT, TOOLCHAINS, describe_package, require_toolchain, run_relax_job

_DIRECTORIES = tuple(sorted(TOOLCHAINS))


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_package_loads(directory: str) -> None:
    provider = load_workflow_package(REPO_ROOT / directory, register=False)
    assert provider.directory == REPO_ROOT / directory
    assert provider.command is not None
    assert not (REPO_ROOT / directory / "run").exists()
    assert provider.workflow_id == directory.replace("vasp-relax-", "vasp.relax-")


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_package_steps_equal_the_runners_own_description(directory: str, tmp_path: Path) -> None:
    require_toolchain(directory)
    provider = load_workflow_package(REPO_ROOT / directory, register=False)
    described = describe_package(directory, tmp_path)
    assert set(described["steps"]) == set(provider.steps)
    assert described["workflow"] == provider.workflow_id


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_package_declaration_matches_the_committed_file(directory: str) -> None:
    provider = load_workflow_package(REPO_ROOT / directory, register=False)
    declared = json.loads((REPO_ROOT / directory / "declaration.json").read_text(encoding="utf-8"))
    assert provider.declarations["workflow"] == declared
    assert declared == json.loads((REPO_ROOT / "vasp-relax-c" / "declaration.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_package_inputs_and_outputs_are_well_formed(directory: str) -> None:
    provider = load_workflow_package(REPO_ROOT / directory, register=False)
    assert provider.inputs == {"structure": "POSCAR"}
    assert set(provider.outputs) == {"relaxed_structure", "total_energy"}
    for metadata in provider.outputs.values():
        for key in ("entry_type", "ref", "description"):
            assert isinstance(metadata.get(key), str) and metadata[key]


def test_plugin_manifest_lists_exactly_the_seven_directories() -> None:
    manifest = parse_plugin_manifest(REPO_ROOT)
    assert set(manifest.workflows) == set(_DIRECTORIES)


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_a_missing_vasp_command_fails_by_name(directory: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HTTK_VASP_COMMAND", raising=False)
    workspace, marker = run_relax_job(directory, tmp_path, vasp_command=False)
    assert marker.kind == "failed"
    failure = workspace.read_state(marker)["failure"]
    assert failure["code"] == "vasp.command_missing"
    assert failure["message"].startswith("no VASP command is configured")
