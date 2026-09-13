"""BL-036: deploy-eb must roll a new version onto the existing environment."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SCRIPTS = (
    REPO / "scripts" / "deploy-eb.ps1",
    REPO / "scripts" / "deploy-eb.sh",
)

FORBIDDEN = (
    "create-environment",
    "cloudformation deploy",
    "eb create",
    "create-application\n",
    "create-application ",
    "create-application`",
)


def _read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text, f"{path} is empty"
    return text


def test_deploy_scripts_exist() -> None:
    for path in SCRIPTS:
        assert path.is_file(), f"missing {path}"


def test_deploy_scripts_update_existing_env_only() -> None:
    for path in SCRIPTS:
        text = _read(path)
        assert "update-environment" in text, f"{path.name} must update the existing env"
        assert "create-application-version" in text, f"{path.name} must create a version, not an app"
        assert "package-eb" in text, f"{path.name} must package before upload"
        lowered = text.replace("`", " ")
        for needle in FORBIDDEN:
            assert needle not in lowered, f"{path.name} must not contain {needle!r}"
        assert "create-environment" not in text


def test_deploy_scripts_default_to_current_lab_env() -> None:
    for path in SCRIPTS:
        text = _read(path)
        assert "openportfo-api-env" in text
        assert "openportfo-api" in text
        assert "7duvngr98b.execute-api.us-east-1.amazonaws.com" in text
        assert "does not exist" in text.lower() or "not found" in text.lower()
