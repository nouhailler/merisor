from __future__ import annotations

import re
import tomllib
from pathlib import Path

from merisor import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pypi_metadata_and_console_entry_point() -> None:
    configuration = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    project = configuration["project"]

    assert project["name"] == "merisor"
    assert project["dynamic"] == ["version"]
    assert project["license"] == "MIT"
    assert project["gui-scripts"]["merisor"] == "merisor.__main__:main"
    assert project["urls"]["Repository"].endswith("nouhailler/merisor.git")
    assert configuration["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "merisor.__version__"
    }
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_release_workflow_builds_and_publishes_pypi_distribution() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m build" in workflow
    assert "python -m twine check dist/*" in workflow
    assert "actions/upload-artifact@v5" in workflow
    assert "actions/download-artifact@v6" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "id-token: write" in workflow
    assert "PYPI_TOKEN" not in workflow
