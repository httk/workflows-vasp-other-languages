"""The Rust package, built and driven end to end; skipped without its toolchain."""

from pathlib import Path

import pytest

from conftest import run_relax_package


def test_the_relax_package_builds_runs_and_collects(tmp_path: Path) -> None:
    run_relax_package("vasp-relax-rust", tmp_path)


def test_the_relax_package_publishes_transactional_data(tmp_path: Path, test_profile) -> None:
    if not test_profile.extended:
        pytest.skip("the transactional-data run only runs under HTTK_TEST_PROFILE=extended")
    run_relax_package("vasp-relax-rust", tmp_path, data_mode="transactional")
