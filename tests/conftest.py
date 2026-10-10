"""Shared fixtures and helpers for the workflows-vasp-other-languages test suite.

The isolation fixtures and the test-depth knob are those of workflows-vasp's
``tests/conftest.py``. The helpers build a package the way ``httk workflow
build`` does, describe a built runner, and drive one relaxation job of a
package end to end: installed (and so built) into a workspace, run by a real
:class:`httk.workflow.TaskManager`, and collected by the package's collector,
against the mock VASP beside this file.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httk.workflow
import pytest
from httk.workflow import TaskManager, Workspace, collect
from httk.workflow.introspection import read_state, resolve_job
from httk.workflow.protocol import JobRef
from httk.workflow.registry import register_workspace
from httk.workflow.scaffold import describe_package_runner, new_job

# Several tests import httk.atomistic (NumPy) while short-lived runner
# processes are spawned; keeping each BLAS/OMP runtime to one thread avoids
# multiplying that across many concurrent runners.
for _thread_limit in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_limit, "1")


@pytest.fixture(autouse=True)
def _isolated_httk_config(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own httk config and data home, and no ambient VASP command.

    This keeps the global workspace registry (``$XDG_CONFIG_HOME/httk/workspaces.json``)
    from leaking between tests or into the developer's real configuration.
    """

    monkeypatch.setenv("HTTK_CONFIG_HOME", str(tmp_path_factory.mktemp("httk-config")))
    monkeypatch.setenv("HTTK_DATA_HOME", str(tmp_path_factory.mktemp("httk-store")))
    # A machine exporting a real VASP command must never run it from a test.
    monkeypatch.delenv("HTTK_VASP_COMMAND", raising=False)


@pytest.fixture(autouse=True)
def _isolated_workflow_logging() -> Iterator[None]:
    """Restore the ``httk.workflow`` logger after every test."""

    logger = logging.getLogger("httk.workflow")
    propagate = logger.propagate
    handlers = list(logger.handlers)
    level = logger.level
    yield
    logger.propagate = propagate
    logger.handlers[:] = handlers
    logger.setLevel(level)


def register_ws(path: object, name: str = "ws") -> str:
    """Register *path* under *name* and return the name."""

    register_workspace(name, str(path))
    return name


@dataclass(frozen=True)
class TestProfile:
    """Select normal or full-depth values without duplicating a test body."""

    name: str

    @property
    def extended(self) -> bool:
        return self.name == "extended"


@pytest.fixture(scope="session", autouse=True)
def test_profile() -> TestProfile:
    """The test-depth knob shared by every profiled test.

    Normal is deliberately the default for direct pytest invocations. Extended
    runs set ``HTTK_TEST_PROFILE=extended``.
    """

    name = os.environ.get("HTTK_TEST_PROFILE", "normal")
    if name not in {"normal", "extended"}:
        raise pytest.UsageError("HTTK_TEST_PROFILE must be 'normal' or 'extended'")
    return TestProfile(name)


REPO_ROOT = Path(__file__).resolve().parent.parent
MOCK_VASP = Path(__file__).resolve().parent / "mock_vasp.py"
LANGUAGES_DIR = Path(httk.workflow.__file__).parent / "languages"

# The executables each package needs to build and run.
TOOLCHAINS = {
    "vasp-relax-ada": ("cc", "gnatmake", "make"),
    "vasp-relax-c": ("cc", "make"),
    "vasp-relax-cpp": ("cc", "g++", "make"),
    "vasp-relax-fortran": ("cc", "gfortran", "make"),
    "vasp-relax-java": ("javac", "java", "make"),
    "vasp-relax-perl": ("perl",),
    "vasp-relax-rust": ("cargo", "make"),
}

POSCAR = """silicon
1.0
2.0 0.0 0.0
0.0 2.0 0.0
0.0 0.0 2.0
Si
2
Direct
0.0000000000 0.0000000000 0.0000000000
0.5000000000 0.5000000000 0.5000000000
"""


def require_toolchain(directory: str) -> None:
    """Skip the calling test when *directory*'s toolchain is not installed."""

    missing = [tool for tool in TOOLCHAINS[directory] if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"{directory} needs {', '.join(missing)}")


def describe_package(directory: str, tmp_path: Path) -> dict[str, Any]:
    """Describe a package's command, building a copy in place first when it is compiled."""

    package = REPO_ROOT / directory
    if not (package / "Makefile").is_file():
        return describe_package_runner(package)
    build = tmp_path / directory
    shutil.copytree(package, build)
    environment = {**os.environ, "HTTK_WORKFLOW_LANGUAGES_DIR": str(LANGUAGES_DIR)}
    completed = subprocess.run(["make"], cwd=build, env=environment, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    # An in-place build leaves the artifacts at their package-relative paths.
    return describe_package_runner(build, artifacts=build)


def failure(ref: JobRef) -> Any:
    """The job's recorded failure (``code``, ``message``, ``details``), or ``None``."""

    state, damaged = read_state(ref)
    assert damaged is None, damaged
    return None if state is None else state.failure


def run_relax_job(
    directory: str, tmp_path: Path, *, publish_data: bool = False, vasp_command: bool = True
) -> tuple[Workspace, JobRef]:
    """Install (and so build) *directory*, run one relaxation job of it to idle, and return the job.

    With *publish_data* the job asks the runner to publish its results into
    ``data/`` too. With *vasp_command* the workspace names the mock VASP;
    without it no VASP command is configured anywhere.
    """

    require_toolchain(directory)
    package = REPO_ROOT / directory
    workspace = Workspace.initialize(tmp_path / "workspace")
    if vasp_command:
        workspace.set_setting("vasp.command", f"{sys.executable} {MOCK_VASP}")
    register_ws(workspace.root)
    structure = tmp_path / "POSCAR"
    structure.write_text(POSCAR, encoding="utf-8")
    parameters = {"publish_data": True} if publish_data else None
    job = new_job(
        workspace, package, inputs={"structure": structure}, parameters=parameters, tag="silicon", install=True
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=300.0)
    return workspace, resolve_job(workspace, job.job_id)


def run_relax_package(directory: str, tmp_path: Path, publish_data: bool = False) -> None:
    """Build, run, and collect one relaxation job of *directory* with the mock VASP."""

    workspace, ref = run_relax_job(directory, tmp_path, publish_data=publish_data)
    assert ref.state == "succeeded", failure(ref)
    payload = ref.path
    state = json.loads((payload / ".httk-job" / "state.json").read_text(encoding="utf-8"))
    assert state["classification"] == "completed"
    assert (payload / "run" / "CONTCAR").is_file()
    published = payload / "data" / "vasp"
    if publish_data:
        assert (published / "CONTCAR").read_text(encoding="utf-8").splitlines()[-1].startswith("0.51")
    else:
        assert not published.exists()

    (item,) = collect(workspace, fail_fast=True, allow_job_collector=True)
    assert set(item.outputs) == {"relaxed_structure", "total_energy"}
    assert not item.unfulfilled
    assert item.outputs["total_energy"].value == pytest.approx(-10.5)
    assert float(item.outputs["relaxed_structure"].sites.reduced_coords[1][0]) == pytest.approx(0.51)
