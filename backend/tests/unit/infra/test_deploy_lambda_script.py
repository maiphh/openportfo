"""BL-037: deploy-lambda must update the existing function and EventBridge crons."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DEPLOY = (
    REPO / "scripts" / "deploy-lambda.ps1",
    REPO / "scripts" / "deploy-lambda.sh",
)
PACKAGE = (
    REPO / "scripts" / "package-lambda.ps1",
    REPO / "scripts" / "package-lambda.sh",
)


def _read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text, f"{path} is empty"
    return text


def test_lambda_scripts_exist() -> None:
    for path in DEPLOY + PACKAGE:
        assert path.is_file(), f"missing {path}"


def test_deploy_lambda_updates_existing_function_only() -> None:
    for path in DEPLOY:
        text = _read(path)
        assert "update-function-code" in text
        assert "openportfo-jobs" in text
        assert "aws lambda create-function" not in text
        assert "cloudformation deploy" not in text
        assert "was not found" in text.lower() or "not found" in text.lower()


def test_deploy_lambda_eventbridge_email_cron() -> None:
    for path in DEPLOY:
        text = _read(path)
        assert "cron(0 17 * * ? *)" in text
        assert "cron(15 17 * * ? *)" in text
        assert "openportfo-job-email" in text
        assert '{"job":"email"}' in text or '{\\"job\\":\\"email\\"}' in text


def test_package_lambda_uses_linux_docker() -> None:
    for path in PACKAGE:
        text = _read(path)
        assert "linux/amd64" in text
        assert "requirements-lambda.txt" in text
        assert "lambda_handler.py" in text
