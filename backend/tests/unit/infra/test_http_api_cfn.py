"""BL-035: HTTP API Gateway proxy must exist in CFN, off by default."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TEMPLATES = (
    REPO / "infra" / "cloudformation-lab.yml",
    REPO / "infra" / "cloudformation.yml",
)
PACKAGE_SCRIPTS = (
    REPO / "scripts" / "package-eb.ps1",
    REPO / "scripts" / "package-eb.sh",
)


def _read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text, f"{path} is empty"
    return text


def test_http_api_resources_are_conditional_and_proxy_only() -> None:
    for path in TEMPLATES:
        text = _read(path)
        assert "CreateHttpApi:" in text
        assert 'Default: "false"' in text
        assert "AWS::ApiGatewayV2::Api" in text
        assert "AWS::ApiGatewayV2::Integration" in text
        assert "IntegrationType: HTTP_PROXY" in text
        assert 'RouteKey: "ANY /api/{proxy+}"' in text
        assert "IntegrationUri: !Sub \"${ApiBackendUrl}/api/{proxy}\"" in text
        assert "Condition: EnableHttpApi" in text
        assert "HttpApiUrl:" in text
        # User REST integration must stay HTTP_PROXY, not Lambda AWS_PROXY.
        integration_block = text.split("HttpApiIntegration:")[1].split("HttpApiRoute:")[0]
        assert "HTTP_PROXY" in integration_block
        assert "AWS_PROXY" not in integration_block


def test_http_api_cors_exposes_csv_filename_header() -> None:
    for path in TEMPLATES:
        text = _read(path)
        assert "content-disposition" in text
        assert "authorization" in text


def test_package_eb_scripts_accept_api_gateway_url() -> None:
    ps1 = _read(PACKAGE_SCRIPTS[0])
    sh = _read(PACKAGE_SCRIPTS[1])
    assert "[string]$ApiUrl" in ps1
    assert "NEXT_PUBLIC_API_URL=$apiUrlBake" in ps1
    assert "API_URL bake OK" in ps1
    assert 'API_URL="${API_URL:-}"' in sh
    assert 'NEXT_PUBLIC_API_URL="$API_URL"' in sh
    assert "API_URL bake OK" in sh
