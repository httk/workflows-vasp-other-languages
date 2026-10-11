"""The language packages share workflows-vasp's vasp-relax declaration and identity."""

import json
import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SIBLING = REPO_ROOT.parent / "workflows-vasp" / "vasp-relax" / "declaration.json"
_DIRECTORIES = tuple(
    sorted(tomllib.loads((REPO_ROOT / "httk_plugin.toml").read_text(encoding="utf-8"))["plugin"]["workflows"])
)
_ID_PATTERN = re.compile(
    r"^https://raw\.githubusercontent\.com/httk/workflows-vasp/refs/tags/wf-decl-v(\d+\.\d+\.\d+)"
    r"/([a-z0-9-]+)/declaration\.json$"
)


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_declaration_identity(directory: str) -> None:
    declaration = json.loads((REPO_ROOT / directory / "declaration.json").read_text(encoding="utf-8"))
    manifest = tomllib.loads((REPO_ROOT / directory / "httk_workflow.toml").read_text(encoding="utf-8"))
    declaration_id = declaration["$id"]
    assert declaration_id == manifest["workflow"]["declaration_uri"]
    match = _ID_PATTERN.fullmatch(declaration_id)
    assert match, declaration_id
    assert match.group(1) == declaration["x-httk-definition"]["version"]
    assert match.group(2) == "vasp-relax"


@pytest.mark.parametrize("directory", _DIRECTORIES)
def test_declaration_is_workflows_vasp_vasp_relax(directory: str) -> None:
    if not _SIBLING.exists():
        pytest.skip("sibling workflows-vasp checkout is absent")
    assert (REPO_ROOT / directory / "declaration.json").read_bytes() == _SIBLING.read_bytes()
