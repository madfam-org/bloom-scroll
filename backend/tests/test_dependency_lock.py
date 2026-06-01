import tomllib
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOCKFILE = BACKEND_ROOT / "poetry.lock"
LINUX_ML_REQUIREMENTS = BACKEND_ROOT / "requirements-ml-linux-cpu.txt"
DOCKERFILE = BACKEND_ROOT / "Dockerfile"


def _locked_packages() -> list[dict[str, Any]]:
    with LOCKFILE.open("rb") as lockfile:
        data = tomllib.load(lockfile)

    return cast(list[dict[str, Any]], data["package"])


def test_poetry_lock_excludes_ml_wheels_managed_by_pip_requirements() -> None:
    """Poetry must not re-resolve torch or transformer wheels after pip installs them."""

    blocked_packages = {
        "sentence-transformers",
        "torch",
        "transformers",
        "triton",
    }
    offenders = [
        package["name"]
        for package in _locked_packages()
        if package["name"] in blocked_packages or package["name"].startswith("nvidia-")
    ]

    assert offenders == []


def test_linux_ml_requirements_pin_cpu_torch_source() -> None:
    """Production ML wheels stay pinned to the PyTorch CPU index."""

    requirements = LINUX_ML_REQUIREMENTS.read_text()
    dockerfile = DOCKERFILE.read_text()

    assert "--index-url https://download.pytorch.org/whl/cpu" in requirements
    assert "--extra-index-url https://pypi.org/simple" in requirements
    assert any(
        line.startswith("torch==") and line.endswith("+cpu")
        for line in requirements.splitlines()
    )
    assert any(
        line.startswith("sentence-transformers==")
        for line in requirements.splitlines()
    )
    assert any(line.startswith("transformers==") for line in requirements.splitlines())
    assert "pip install -r requirements-ml-linux-cpu.txt" in dockerfile
