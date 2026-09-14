"""Write OpenPortfo_Architecture.drawio from the icon files (dark AWS-icon layout)."""

from __future__ import annotations

import base64
from pathlib import Path
from xml.sax.saxutils import escape

ICONS = Path(r"D:\rmit\cloud\a3\docs\solution-architecture\doc_images\_icons")
OUT = Path(r"D:\rmit\cloud\a3\docs\diagrams\OpenPortfo_Architecture.drawio")

AWS = (
    "sketch=0;outlineConnect=0;fontColor=#FFFFFF;gradientColor=none;"
    "strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;"
    "align=center;html=1;fontSize=11;fontStyle=1;aspect=fixed;"
    "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};fillColor={fill};"
)
HINT = "text;html=1;align=center;fontSize=10;fontColor=#B5B5B5;fontFamily=Arial;strokeColor=none;fillColor=none;"
SEC = "text;html=1;align=left;fontStyle=1;fontSize=13;fontFamily=Arial;strokeColor=none;fillColor=none;fontColor={color};"
EDGE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;html=1;endArrow=block;"
    "endFill=1;strokeWidth=1.5;strokeColor={color};fontSize=11;fontColor={color};"
    "fontFamily=Arial;labelBackgroundColor=#111111;exitX={ex};exitY={ey};entryX={enx};entryY={eny};"
)


def data_uri(path: Path) -> str:
    raw = path.read_bytes()
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def aws_icon(vid: str, icon: str, fill: str, label: str, x: int, y: int, size: int = 72) -> str:
    style = AWS.format(icon=icon, fill=fill)
    return (
        f'<mxCell id="{vid}" parent="1" vertex="1" style="{style}" value="{escape(label)}">'
        f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>'
    )


def hint(vid: str, text: str, x: int, y: int, w: int = 140, h: int = 36) -> str:
    return (
        f'<mxCell id="{vid}" parent="1" vertex="1" style="{HINT}" value="{escape(text)}">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def section(vid: str, text: str, color: str, x: int, y: int) -> str:
    return (
        f'<mxCell id="{vid}" parent="1" vertex="1" style="{SEC.format(color=color)}" value="{escape(text)}">'
        f'<mxGeometry x="{x}" y="{y}" width="200" height="20" as="geometry"/></mxCell>'
    )


def image_icon(vid: str, path: Path, label: str, x: int, y: int, size: int = 72) -> str:
    uri = data_uri(path)
    style = (
        "shape=image;html=1;verticalLabelPosition=bottom;verticalAlign=top;align=center;"
        f"aspect=fixed;imageAspect=0;fontColor=#FFFFFF;fontSize=11;fontStyle=1;fontFamily=Arial;"
        f"labelBackgroundColor=none;image={uri}"
    )
    return (
        f'<mxCell id="{vid}" parent="1" vertex="1" style="{style}" value="{escape(label)}">'
        f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>'
    )


def edge(vid: str, source: str, target: str, label: str, color: str, ex=0.5, ey=1, enx=0.5, eny=0, points=None) -> str:
    style = EDGE.format(color=color, ex=ex, ey=ey, enx=enx, eny=eny)
    pts = ""
    if points:
        inner = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        pts = f'<Array as="points">{inner}</Array>'
    lab = escape(label)
    return (
        f'<mxCell id="{vid}" parent="1" source="{source}" target="{target}" edge="1" style="{style}" value="{lab}">'
        f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
    )


def main() -> None:
    cells = [
        '<mxCell id="0"/>',
        '<mxCell id="1" parent="0"/>',
        '<mxCell id="title" parent="1" vertex="1" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontStyle=1;fontSize=22;fontColor=#FFFFFF;fontFamily=Arial;" value="OpenPortfo — System Architecture">'
        '<mxGeometry x="350" y="12" width="700" height="30" as="geometry"/></mxCell>',
        section("fe", "Frontend", "#8C4FFF", 220, 52),
        section("be", "Backend", "#ED7100", 560, 52),
        section("dj", "Data &amp; Jobs", "#C925D1", 1000, 52),
        section("ext", "External APIs", "#2E7D32", 220, 488),
        aws_icon("cognito", "cognito", "#DD344C", "Amazon Cognito", 74, 112),
        hint("cognito_h", "Hosted UI · JWT&#xa;email / Google", 40, 198),
        image_icon("user", ICONS / "user.png", "User", 74, 340, 64),
        hint("user_h", "Loads OpenPortfo&#xa;in the browser", 40, 418),
        aws_icon("apigw", "api_gateway", "#8C4FFF", "Amazon API Gateway", 254, 112),
        hint("apigw_h", "HTTP API&#xa;REST /api/*", 220, 198),
        aws_icon("eb", "elastic_beanstalk", "#ED7100", "Elastic Beanstalk", 474, 112),
        hint("eb_h", "Next.js UI + FastAPI&#xa;auth, portfolio, admin,&#xa;watchlist, holdings, chat", 440, 198, 140, 50),
        aws_icon("ddb", "dynamodb", "#C925D1", "Amazon DynamoDB", 724, 96),
        hint("ddb_h", "Users, holdings,&#xa;watchlist, news, cache", 690, 182),
        aws_icon("lambda", "lambda", "#ED7100", "AWS Lambda", 1014, 96),
        hint("lambda_h", "Scheduled jobs:&#xa;RSS, prices, snapshot, email", 980, 182, 140, 40),
        image_icon("gmail", ICONS / "gmail.svg", "Gmail SMTP", 1214, 96),
        hint("gmail_h", "Daily portfolio&#xa;email summary", 1180, 182),
        aws_icon("s3", "s3", "#7AA116", "Amazon S3", 724, 286),
        hint("s3_h", "History + snapshots", 690, 372, 140, 24),
        aws_icon("athena", "athena", "#8C4FFF", "Amazon Athena", 894, 286),
        hint("athena_h", "SQL analytics on&#xa;portfolio snapshots", 860, 372),
        aws_icon("evb", "eventbridge", "#E7157B", "Amazon EventBridge", 1014, 330),
        hint("evb_h", "Cron schedule&#xa;(email time from Admin)", 980, 416),
        image_icon("cg", ICONS / "coingecko.png", "Coingecko", 314, 530),
        hint("cg_h", "Crypto prices&#xa;&amp; history", 280, 616),
        image_icon("vn", ICONS / "vnstock.png", "Vnstock", 484, 530),
        hint("vn_h", "VN stock prices&#xa;&amp; history", 450, 616),
        image_icon("or", ICONS / "openrouter.png", "OpenRouter", 654, 530),
        hint("or_h", "Chat LLM&#xa;server-side only", 620, 616),
        # Arrows stop at labels / node boxes; they do not cross captions.
        edge("e_signin", "user", "cognito", "Sign in", "#DEDEDE", 0.5, 0, 0.5, 1),
        edge("e_rest", "user", "apigw", "REST /api/*", "#DEDEDE", 1, 0.5, 0.5, 1, [(290, 372)]),
        edge("e_ui", "user", "eb", "Loads UI · SSE chat", "#DEDEDE", 1, 0.65, 0.5, 1, [(510, 404)]),
        edge("e_proxy", "apigw", "eb", "HTTP_PROXY", "#DEDEDE", 1, 0.5, 0, 0.5),
        edge("e_ddb", "eb", "ddb", "Read / write app data", "#DEDEDE", 1, 0.35, 0, 0.45),
        edge("e_s3", "eb", "s3", "Read / write", "#DEDEDE", 0.85, 1, 0, 0.5, [(640, 322)]),
        edge("e_ath", "s3", "athena", "", "#DEDEDE", 1, 0.5, 0, 0.5),
        edge("e_evb", "evb", "lambda", "Triggers on schedule", "#E7157B", 0.5, 0, 0.5, 1),
        edge("e_news", "lambda", "ddb", "Writes news / snapshots / cache", "#DEDEDE", 0, 0.45, 1, 0.35),
        edge("e_smtp", "lambda", "gmail", "SMTP send", "#DEDEDE", 1, 0.45, 0, 0.45),
        edge("e_cg", "eb", "cg", "On demand / refresh", "#7AA116", 0.5, 1, 0.5, 0, [(510, 510), (350, 510)]),
        edge("e_vn", "eb", "vn", "", "#7AA116", 0.5, 1, 0.5, 0, [(510, 510), (520, 510)]),
        edge("e_or", "eb", "or", "Chat SSE", "#7AA116", 0.5, 1, 0.5, 0, [(510, 510), (690, 510)]),
        '<mxCell id="foot" parent="1" vertex="1" style="text;html=1;align=center;fontSize=10;fontColor=#9A9A9A;fontFamily=Arial;strokeColor=none;fillColor=none;" value="OpenPortfo · User → Cognito (login) · UI from Elastic Beanstalk · REST /api/* → API Gateway → FastAPI → DynamoDB / S3 / Athena · Backend → CoinGecko + vnstock + OpenRouter · EventBridge → Lambda → Gmail SMTP">'
        '<mxGeometry x="40" y="700" width="1320" height="28" as="geometry"/></mxCell>',
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" agent="OpenPortfo">'
        '<diagram id="openportfo-arch" name="OpenPortfo Architecture">'
        '<mxGraphModel dx="1400" dy="740" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" pageHeight="740" background="#111111" math="0" shadow="0">'
        "<root>"
        + "".join(cells)
        + "</root></mxGraphModel></diagram></mxfile>\n"
    )
    OUT.write_text(xml, encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
