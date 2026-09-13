"""Build OpenPortfo_Solution_Architecture.docx using the proposal.docx styles."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree

ROOT = Path(__file__).resolve().parent
TEMPLATE = Path(r"D:\rmit\cloud\a3\docs\proposal\proposal.docx")
OUT = ROOT / "OpenPortfo_Solution_Architecture.docx"
IMAGES = ROOT / "doc_images"

NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
GRAY = RGBColor(0x40, 0x40, 0x40)
HEADER_GRAY = RGBColor(0x59, 0x59, 0x59)


def _set_run_font(run, size=None, bold=None, color=None, italic=None):
    run.font.name = "Arial"
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), "Arial")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def _spacing(p, before=0, after=160, line=276):
    pPr = p._p.get_or_add_pPr()
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:before"), str(before))
    spacing.set(qn("w:after"), str(after))
    spacing.set(qn("w:line"), str(line))
    spacing.set(qn("w:lineRule"), "auto")


def add_body(doc, text, *, size=11, after=160, first_line=None, align=None):
    p = doc.add_paragraph(style="Normal")
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    _set_run_font(run, size=size, bold=False)
    _spacing(p, before=0, after=after, line=276)
    if first_line:
        p.paragraph_format.first_line_indent = Inches(first_line)
    return p


def add_cover_line(doc, text, *, size, bold=False, color=None, after=80, before=0):
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    _set_run_font(run, size=size, bold=bold, color=color or RGBColor(0, 0, 0))
    _spacing(p, before=before, after=after, line=240)
    return p


def add_h1(doc, text):
    p = doc.add_paragraph(text, style="Heading 1")
    for run in p.runs:
        _set_run_font(run, size=16, bold=True, color=NAVY)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph(text, style="Heading 2")
    for run in p.runs:
        _set_run_font(run, size=13, bold=True, color=BLUE)
    return p


def add_h3(doc, text):
    p = doc.add_paragraph(text, style="Heading 3")
    for run in p.runs:
        _set_run_font(run, size=12, bold=True, color=GRAY)
    return p


def add_bullet(doc, lead, rest):
    p = doc.add_paragraph(style="List Paragraph")
    pPr = p._p.get_or_add_pPr()
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    numId = OxmlElement("w:numId")
    numId.set(qn("w:val"), "4")
    numPr.append(ilvl)
    numPr.append(numId)
    pPr.append(numPr)
    _spacing(p, before=0, after=80, line=276)
    r1 = p.add_run(lead)
    _set_run_font(r1, size=11, bold=True)
    r2 = p.add_run(rest)
    _set_run_font(r2, size=11, bold=False)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    _set_run_font(run, size=10, bold=True)
    _spacing(p, before=80, after=200, line=240)
    return p


def add_figure(doc, filename, caption, width=6.5):
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _spacing(p, before=80, after=40, line=240)
    run = p.add_run()
    run.add_picture(str(IMAGES / filename), width=Inches(width))
    add_caption(doc, caption)


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "22")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Arial")
    rFonts.set(qn("w:hAnsi"), "Arial")
    rPr.extend([rFonts, color, u, sz])
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def shade_cell(cell, fill, font_color=None, bold=False, size=8.5):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right", "start", "end"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "2")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "1F4E79")
        borders.append(el)
    tcPr.append(borders)
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    tcPr.append(vAlign)
    for p in cell.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if fill == "1F4E79" else WD_ALIGN_PARAGRAPH.LEFT
        _spacing(p, before=40, after=40, line=240)
        for run in p.runs:
            _set_run_font(
                run,
                size=size,
                bold=bold or fill == "1F4E79",
                color=RGBColor(0xFF, 0xFF, 0xFF) if fill == "1F4E79" else (font_color or RGBColor(0, 0, 0)),
            )


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.autofit = True
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        shade_cell(cell, "1F4E79", bold=True, size=8.5)
    for r_i, row in enumerate(rows):
        fill = "FFFFFF" if r_i % 2 == 0 else "EEF3F8"
        for c_i, val in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            cell.text = val
            shade_cell(cell, fill, size=8)
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
    return table


def set_header(doc):
    header = doc.sections[0].header
    header.is_linked_to_previous = False
    p = header.paragraphs[0]
    p.clear()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "1F4E79")
    pBdr.append(bottom)
    pPr.append(pBdr)
    run = p.add_run("OpenPortfo — Solution Architecture  |  RMIT Cloud Computing Assessment 3")
    _set_run_font(run, size=8, color=HEADER_GRAY)
    _spacing(p, before=0, after=120, line=240)


def page_break(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_break(WD_BREAK.PAGE)


def clone_template() -> Document:
    doc = Document(str(TEMPLATE))
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)
    return doc


def build():
    doc = clone_template()
    set_header(doc)

    # --- Cover ---
    add_cover_line(doc, "RMIT University", size=12, bold=True, after=40)
    add_cover_line(doc, "Cloud Computing — Assessment 3", size=11, color=GRAY, after=0)
    for _ in range(8):
        add_cover_line(doc, "\u00a0", size=14, bold=True, after=80)
    add_cover_line(doc, "SOLUTION ARCHITECTURE", size=14, bold=True, after=120)
    add_cover_line(
        doc,
        "OpenPortfo: A Cloud-Based Crypto and Vietnam Stock Portfolio Tracking System",
        size=18,
        bold=True,
        after=200,
    )
    add_cover_line(doc, "Student ID: s3927049", size=10, after=40)
    add_cover_line(doc, "Student name: Mai Gia Phu", size=10, after=40)
    add_cover_line(doc, "September 2026", size=10, after=40)

    page_break(doc)

    # --- TOC ---
    add_h1(doc, "Table of Contents")
    toc = [
        "1. Links",
        "2. Summary",
        "3. Introduction",
        "     3.1 Motivation",
        "     3.2 High-level view",
        "     3.3 Beneficiaries",
        "4. Related work",
        "5. System Architecture",
        "     5.1 Architectural diagrams",
        "     5.2 System description",
        "     5.3 Datasets, data structures and APIs",
        "6. References",
    ]
    for line in toc:
        p = add_body(doc, line, size=11, after=40)
        p.paragraph_format.line_spacing = 1.15

    page_break(doc)

    # --- 1. Links ---
    add_h1(doc, "1. Links")
    add_body(
        doc,
        "The application is deployed on an AWS Academy Learner Lab account in us-east-1. Lab sessions are torn down when the lab stops, so the public hostname can change after a new Start Lab. The values below were live on 13 September 2026.",
    )

    p = add_body(doc, "", after=40)
    p.clear()
    r = p.add_run("Live application URL: ")
    _set_run_font(r, size=11, bold=True)
    add_hyperlink(
        p,
        "http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com",
        "http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com",
    )
    _spacing(p, after=80)

    p = add_body(doc, "", after=40)
    p.clear()
    r = p.add_run("REST API Gateway: ")
    _set_run_font(r, size=11, bold=True)
    add_hyperlink(
        p,
        "https://7duvngr98b.execute-api.us-east-1.amazonaws.com",
        "https://7duvngr98b.execute-api.us-east-1.amazonaws.com",
    )
    r = p.add_run("  (route ANY /api/{proxy+} → Elastic Beanstalk FastAPI)")
    _set_run_font(r, size=11)
    _spacing(p, after=80)

    p = add_body(doc, "", after=40)
    p.clear()
    r = p.add_run("Source code repository: ")
    _set_run_font(r, size=11, bold=True)
    add_hyperlink(p, "https://github.com/maiphh/openportfo", "https://github.com/maiphh/openportfo.git")
    r = p.add_run("  (no AWS credentials are stored in the repository)")
    _set_run_font(r, size=11)
    _spacing(p, after=80)

    p = add_body(doc, "", after=40)
    p.clear()
    r = p.add_run("Cognito Hosted UI: ")
    _set_run_font(r, size=11, bold=True)
    add_hyperlink(
        p,
        "https://openportfo-11f1.auth.us-east-1.amazoncognito.com",
        "https://openportfo-11f1.auth.us-east-1.amazoncognito.com",
    )
    _spacing(p, after=80)

    add_body(
        doc,
        "Public datasets: the project does not ship a large static dataset. Market prices come from CoinGecko and vnstock at run time. News items come from public RSS feeds configured on the Admin page. Daily portfolio snapshots are generated by the application and stored in S3 for Athena.",
    )

    # --- 2. Summary ---
    add_h1(doc, "2. Summary")
    add_body(
        doc,
        "OpenPortfo is a web application that lets one person track cryptocurrency and Vietnam-listed stock holdings in a single place. The user signs in, searches assets, saves a watchlist and holdings with quantity and cost, and sees market value, profit and loss, allocation charts, and a history chart. Prices are loaded on demand and cached; they are not streamed. A daily Lambda job stores a portfolio snapshot, pulls RSS news that matches the user’s symbols, and can send a summary email. An admin page controls RSS sources, job flags, cache time, and USD/VND rates.",
    )
    add_body(
        doc,
        "The live cloud split is simple. The browser loads the Next.js static UI from Elastic Beanstalk. REST calls under /api/* go to Amazon API Gateway, which forwards them to FastAPI on the same Beanstalk environment. Chat streaming stays on Beanstalk because the Gateway 30-second timeout is too short. Scheduled work is EventBridge → Lambda only. DynamoDB holds live records. S3 holds history and snapshot files. Athena runs SQL on those snapshot files.",
    )

    # --- 3. Introduction ---
    add_h1(doc, "3. Introduction")
    add_h2(doc, "3.1 Motivation")
    add_body(
        doc,
        "Crypto wallets and Vietnam broker apps do not share a portfolio view. People end up with two screens plus a spreadsheet, so total value, allocation, and profit and loss are hard to see together. Paid multi-asset products are usually built for US or global tickers, not HOSE names next to Bitcoin. A student cloud project also has a hard spend cap, so a real-time exchange or a large always-on cluster is the wrong shape.",
    )
    add_body(
        doc,
        "OpenPortfo is built to close that gap with a small AWS stack: one login, one dashboard, on-demand prices, keyword-matched news, and an optional daily email, without executing trades.",
    )

    add_h2(doc, "3.2 High-level view")
    add_body(
        doc,
        "At a high level the product is a personal portfolio tracker, not a broker. After login the user can search Bitcoin or a Vietnam ticker such as VNM, add it to a watchlist or as a holding, and open a dashboard that shows value, cost, PnL, a pie chart, and a table. A Refresh button updates quotes through the backend. Asset pages show a history chart. A news list is filled by a nightly job. A chat bubble can answer questions about the user’s own holdings. An admin user can change RSS feeds, turn jobs on or off, and refresh FX rates.",
    )
    add_body(
        doc,
        "Two traffic paths stay separate on purpose. User clicks go through the browser, API Gateway (for REST), and FastAPI. Nightly work is EventBridge calling Lambda. The browser never talks to CoinGecko, vnstock, or DynamoDB itself.",
    )

    add_h2(doc, "3.3 Beneficiaries")
    add_bullet(
        doc,
        "Individual investors. ",
        "People who hold both crypto and Vietnam stocks and want one dashboard instead of two apps and a sheet.",
    )
    add_bullet(
        doc,
        "A demo examiner / tutor. ",
        "A live URL, tables and charts, a clear AWS story (Beanstalk, Gateway, Lambda, DynamoDB, S3, Athena), and evidence of a scheduled job.",
    )
    add_bullet(
        doc,
        "A seeded admin. ",
        "Someone who can change RSS sources, job flags, cache TTL, and FX rates without a new deploy.",
    )

    # --- 4. Related work ---
    add_h1(doc, "4. Related work")
    add_body(
        doc,
        "Several products already track portfolios, but they split along asset-class lines. Table 1 places OpenPortfo next to tools that students and retail investors actually use.",
    )
    add_table(
        doc,
        ["Product", "Crypto", "VN stocks", "Unified view", "News", "Email / chat", "Deploy model"],
        [
            ["CoinMarketCap Portfolio", "Yes", "No", "Crypto only", "Site news", "Limited", "SaaS web"],
            ["Delta / Blockfolio-style apps", "Yes", "No", "Crypto only", "Alerts", "Push", "Mobile SaaS"],
            ["Yahoo Finance", "Limited", "Limited VN", "Global multi-asset", "Yes", "Alerts", "SaaS"],
            ["CafeF / TCBS tools", "No", "Yes", "VN equities", "Market news", "Varies", "Local portals"],
            ["Google Sheets trackers", "Manual", "Manual", "If the user builds it", "No", "No", "DIY"],
            ["OpenPortfo (this work)", "Yes (CoinGecko)", "Yes (vnstock)", "Crypto + VN", "RSS + keywords", "Daily email + chat", "AWS self-deploy"],
        ],
    )
    add_caption(doc, "Table 1. Related products compared with OpenPortfo.")
    add_body(
        doc,
        "CoinMarketCap and Delta-class apps are strong for crypto and weak for Vietnam broker holdings. Yahoo Finance covers many global markets, but Vietnam symbols and a free automated digest are not the point of that product. CafeF and TCBS tools are the usual place for HOSE/HNX prices and local news; they do not value a crypto wallet next to those stocks. Spreadsheet trackers can do anything once, then rot.",
    )
    add_body(
        doc,
        "OpenPortfo is not a full brokerage and not a production fintech product. It is a complete student AWS system: dual market APIs, Beanstalk user APIs versus Lambda schedules, admin-managed RSS, Athena-ready snapshots, and a Cognito login. That combination is what Assessment 3 asks for, and it is what the related tools above do not put on one cheap cloud stack.",
    )

    # --- 5. System Architecture ---
    add_h1(doc, "5. System Architecture")
    add_h2(doc, "5.1 Architectural diagrams")
    add_body(
        doc,
        "Figure 1 is the whole system. Figures 2 and 3 show how a click in the UI reaches other components. Figure 4 is the nightly path, which the browser never starts. Table 2 is the data layout. Figure 5 splits login and chat, because those two flows do not share the same front door.",
    )

    add_figure(
        doc,
        "fig1_high_level.png",
        "Figure 1. OpenPortfo high-level architecture (AWS service icons). Each icon states the component function.",
        width=6.5,
    )
    add_body(
        doc,
        "The intended production UI path is CloudFront in front of an S3 website bucket. AWS Academy blocks CloudFront in this lab, so the live demo serves the same Next.js static export from Elastic Beanstalk. S3 is still used for history and snapshot files. REST still uses API Gateway. That lab constraint does not change the two-path design: user requests versus EventBridge jobs.",
    )

    add_figure(
        doc,
        "fig2_client_operations.png",
        "Figure 2. How each client-interface operation invokes the rest of the system.",
        width=6.5,
    )
    add_body(
        doc,
        "Figure 2 is the map the assignment asks for: each UI action, the first AWS entry, the FastAPI call, and what is read or written. Three rules stay fixed. The browser does not call market APIs. Lambda is not a public HTTP API. Chat streaming does not go through API Gateway.",
    )

    add_figure(
        doc,
        "fig3_portfolio_sequence.png",
        "Figure 3. Sequence for view-portfolio and Refresh. This is the main request-path interaction.",
        width=6.5,
    )
    add_body(
        doc,
        "On a warm cache, GET /api/portfolio is FastAPI plus DynamoDB only. Refresh, or a cache miss, adds CoinGecko and vnstock, then writes PriceCache so the next view is cheap. FX is not fetched here. Conversion uses the last rates an admin stored.",
    )

    add_figure(
        doc,
        "fig4_scheduled_jobs.png",
        "Figure 4. Schedule path: EventBridge invokes Lambda. Four jobs share one function and branch on event.job. Email leaves AWS through Gmail SMTP.",
        width=6.5,
    )
    add_body(
        doc,
        "EventBridge rules in us-east-1 run news, price, and snapshot at 17:00 UTC (00:00 ICT) and email at 17:15 UTC. The Lambda name is openportfo-jobs. Admin can also run the news job from the UI; that is still FastAPI invoking Lambda, not the browser calling Lambda. Athena is not a fifth job: it reads snapshot files after they already sit in S3.",
    )

    add_body(
        doc,
        "Table 2 is the data layout the assignment asks to show with the diagrams: every DynamoDB table, its keys, and the S3 prefixes Athena reads. userId is always the Cognito sub. The table prefix in the lab is openportfo-.",
    )
    add_table(
        doc,
        ["Store", "Name", "Keys", "Main attributes", "Written by"],
        [
            ["DynamoDB", "users", "PK userId", "email, name, role, keywords, emailOptIn, currency", "FastAPI /auth/me"],
            ["DynamoDB", "holdings", "PK userId, SK HOLD#type#symbol", "qty, avgCost, currency, note", "Holdings API"],
            ["DynamoDB", "watchlist", "PK userId, SK WATCH#type#symbol", "addedAt", "Watchlist API"],
            ["DynamoDB", "price-cache", "PK type#symbol", "price, currency, asOf, ttl", "FastAPI + price job"],
            ["DynamoDB", "news", "PK date, SK source#hash", "title, url, symbols, keywords", "News Lambda"],
            ["DynamoDB", "snapshots", "PK userId, SK SNAP#date", "lines, totals, fx", "Snapshot Lambda"],
            ["DynamoDB", "settings", "PK SETTINGS, SK GLOBAL", "jobs, cache TTL, chat model", "Admin API"],
            ["DynamoDB", "fx", "PK FX, SK LATEST", "rates, asOf, lastRefreshStatus", "Admin FX refresh"],
            ["DynamoDB", "rss", "PK RSS, SK sourceId", "name, url, enabled", "Admin RSS API"],
            ["DynamoDB", "job-runs", "PK JOB#type, SK runAt", "status, message, counts", "Lambda / admin run"],
            ["DynamoDB", "chat-idempotency", "PK userId, SK requestId", "expiresAt (TTL)", "Chat API"],
            ["S3", "snapshots/", "userId={id}/dt={YYYY-MM-DD}/part.json", "lines, totalsByCurrency, fx", "Snapshot Lambda"],
            ["S3", "history/", "{crypto|stock}/{id}/{range}.json", "OHLCV / market_chart cache", "FastAPI + price job"],
            ["S3", "athena-results/", "query output prefix", "Athena result files", "Athena"],
        ],
        col_widths=[1.1, 1.4, 1.7, 1.3, 1.0],
    )
    add_caption(doc, "Table 2. DynamoDB tables and S3 object layout used by Athena.")

    add_figure(
        doc,
        "fig6_login_and_chat.png",
        "Figure 5. Login uses Cognito plus API Gateway. Chat SSE uses the Beanstalk origin only.",
        width=6.5,
    )

    add_h2(doc, "5.2 System description")
    add_body(
        doc,
        "Assessment 3 asks for AWS services under Compute, Containers, Storage, Networking and Content Delivery, Database, and Analytics. Tables 3–7 use those console categories. Containers is unused: Elastic Beanstalk is the Compute host, not ECS or EKS. Tables 8–10 cover extra AWS services and the third-party APIs the live system actually calls. Each row states the component function and who invokes it.",
    )

    add_h3(doc, "Compute")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Elastic Beanstalk [2]",
                "Hosts FastAPI (JWT check, CRUD, portfolio maths, chat SSE) and, in this lab, the Next.js static UI plus /health",
                "Browser (UI pages and POST /api/chat/stream); API Gateway HTTP_PROXY for REST /api/*",
                "DynamoDB, S3, Cognito JWKS, CoinGecko, vnstock, OpenRouter; Lambda only for admin “run news”",
            ],
            [
                "AWS Lambda openportfo-jobs [9]",
                "One function, four jobs: news (RSS match), price (warm cache), snapshot (value every user), email (PnL digest)",
                "EventBridge cron; FastAPI admin POST to run the news job",
                "RSS URLs, CoinGecko, vnstock, DynamoDB, S3, Gmail SMTP. Not a public HTTP API",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 3. Compute services.")

    add_h3(doc, "Storage")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon S3 [6]",
                "Data bucket for price-history JSON, daily snapshot files, and Athena query output. Not a public website bucket",
                "FastAPI (history cache) and the price / snapshot Lambda jobs",
                "Athena reads the snapshots/ prefix. Intended UI hosting on S3+CloudFront is blocked in Academy, so the UI is on Beanstalk",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 4. Storage services.")

    add_h3(doc, "Networking and Content Delivery")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon API Gateway HTTP API [3]",
                "REST front door. API id 7duvngr98b proxies ANY /api/{proxy+} with HTTP_PROXY. CORS allows the Beanstalk UI origin. Not an authorizer",
                "Browser REST clients (execute-api hostname)",
                "Elastic Beanstalk FastAPI. Does not front /, /_next/*, /health, chat SSE, or Lambda",
            ],
            [
                "Amazon CloudFront",
                "Designed as the UI CDN in front of an S3 website bucket",
                "Not live in this lab — AWS Academy blocks CloudFront",
                "Would fetch static Next.js files from S3. Lab substitute: Beanstalk serves the same export",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 5. Networking and Content Delivery services.")

    add_h3(doc, "Database")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon DynamoDB [5]",
                "Operational store (on-demand): users, holdings, watchlist, price-cache (TTL), news, snapshots, settings, fx, rss, job-runs, chat-idempotency. Keys in Section 5.3. Passwords are never stored",
                "FastAPI adapters on every authenticated request; Lambda jobs for news, cache, snapshots, job-runs",
                "Domain code does not import boto3. userId is the Cognito sub",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 6. Database services.")

    add_h3(doc, "Analytics")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon Athena [7]",
                "SQL on snapshot files (database openportfo, table portfolio_snapshots_raw, JSON SerDe). Not on the dashboard hot path",
                "Saved query openportfo-latest-snapshots after the snapshot job has written S3. Not EventBridge and not the browser",
                "S3 snapshots/ prefix; results land under athena-results/ so scans stay small",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 7. Analytics services.")

    add_h3(doc, "Application Integration")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon EventBridge [8]",
                "Clock for unattended jobs. Four ENABLED rules: news, price, snapshot at cron(0 17 * * ? *); email at cron(15 17 * * ? *)",
                "Schedule only (00:00 / 00:15 ICT). The browser never calls EventBridge",
                "Lambda openportfo-jobs with {\"job\": \"news\"|\"price\"|\"snapshot\"|\"email\"}",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 8. Application Integration services.")

    add_h3(doc, "Security, Identity, and Compliance")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Amazon Cognito [4]",
                "User Pool us-east-1_YRFHh9x1r. Hosted UI for email/password and optional Google. Issues ID tokens. SPA is a public app client",
                "User Sign in / Sign up / Google from the browser",
                "Browser keeps the ID token and sends Authorization: Bearer. FastAPI verifies JWKS (signature, issuer, audience, expiry)",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 9. Identity services.")

    add_h3(doc, "Client interface and third-party APIs")
    add_table(
        doc,
        ["Component", "Function", "Invoked by", "Talks to"],
        [
            [
                "Next.js static CSR [12]",
                "Markets, watchlist, portfolio, asset detail, settings, admin, Cognito callback. Charts and tables render from FastAPI JSON. No Next.js server on AWS",
                "User in the browser",
                "REST via API Gateway; UI files and chat SSE from Elastic Beanstalk. Never CoinGecko or DynamoDB directly",
            ],
            [
                "Gmail SMTP",
                "Daily portfolio email (PnL, holdings, matched news) to opt-in users. Academy denies SES, so the live path is smtp.gmail.com:587 STARTTLS. SES is not used",
                "Lambda email job at 00:15 ICT when admin jobs.email and user emailOptIn are on",
                "Gmail only. App Password stays in Lambda env, not in Git",
            ],
            [
                "CoinGecko [1]",
                "Graded third-party API. Crypto search, USD quotes, market_chart history",
                "FastAPI on search / quote / refresh / history; price Lambda",
                "Results cached in DynamoDB PriceCache and history objects in S3",
            ],
            [
                "vnstock [10]",
                "Graded third-party API. HOSE/HNX search, last price, OHLCV",
                "FastAPI on search / quote / refresh / history; price Lambda",
                "Same cache path as CoinGecko. Last good price kept if a fetch fails",
            ],
            [
                "Public RSS",
                "News ingest. Not a vendor SDK; Lambda GETs feed XML from admin URLs",
                "News Lambda (cron or admin run)",
                "Items matching symbols or keywords written to the news table",
            ],
            [
                "OpenRouter [14]",
                "Chat LLM. FastAPI sends holdings as context and streams the reply",
                "POST /api/chat/stream on Beanstalk (not Gateway)",
                "DynamoDB chat-idempotency TTL only; no transcript store",
            ],
            [
                "ExchangeRate-API [11]",
                "USD/VND rates. Admin on-demand only, not the portfolio hot path",
                "POST /api/admin/fx/refresh",
                "Stored in the fx table. A failed refresh keeps the last good rates",
            ],
        ],
        col_widths=[1.5, 1.9, 1.7, 1.4],
    )
    add_caption(doc, "Table 10. Client interface and third-party APIs.")

    add_h3(doc, "Why this shape")
    add_body(
        doc,
        "User traffic and background work are split so each AWS service has one job. Elastic Beanstalk, API Gateway, and Lambda are invoked by the UI, by FastAPI, or by EventBridge — not only from the console. DynamoDB, S3, and Athena cover records, files, and SQL. Cognito is the login service. EventBridge is the clock. Daily mail uses Gmail SMTP because Academy blocks SES. Cost stays under the USD $50 cap by using one small Beanstalk instance, on-demand DynamoDB, Lambda free tier, and Athena queries that scan snapshot JSON rather than large scans.",
    )

    add_h2(doc, "5.3 Datasets, data structures and APIs")
    add_h3(doc, "Datasets")
    add_body(
        doc,
        "There is no downloaded CSV that the marker must install. Three data sources feed the system, and one dataset is produced by it.",
    )
    add_bullet(
        doc,
        "CoinGecko (live). ",
        "Crypto instruments, current USD prices, and market_chart history. Free-tier limits are the reason for PriceCache TTL and batch quotes.",
    )
    add_bullet(
        doc,
        "vnstock / public broker APIs (live). ",
        "Vietnam listed symbols, last price, and OHLCV. These endpoints can change; FastAPI keeps the last cached price if a fetch fails.",
    )
    add_bullet(
        doc,
        "Public RSS (live). ",
        "Feed URLs are stored in the rss table and edited on /admin. Items are not a file in the repo. Matching is substring on title against symbols and user keywords.",
    )
    add_bullet(
        doc,
        "Generated snapshots (S3). ",
        "Each night (or on demand) the snapshot job writes part.json per user and date. That object is the Athena dataset. Fields: userId, date, lines[], totalsByCurrency{}, fx{status, base, asOf, rates}.",
    )

    add_h3(doc, "Data structures")
    add_body(
        doc,
        "Table 2 (Section 5.1) is the DynamoDB and S3 layout used in the lab. Physical tables are separate on purpose so the demo is easy to walk through. userId is always the Cognito sub. Portfolio maths are done in FastAPI, not in Athena:",
    )
    add_body(
        doc,
        "marketValue = Σ (qty × price);  costBasis = Σ (qty × avgCost);  pnl = marketValue − costBasis;  allocation = lineValue / marketValue. Crypto lines are primarily USD; VN stocks are VND; display conversion uses stored FX rates only.",
        after=200,
    )

    add_h3(doc, "Application APIs")
    add_body(
        doc,
        "Table 11 lists the FastAPI routes the UI actually calls. Unless noted, they are reached as https://{api-id}.execute-api.us-east-1.amazonaws.com/api/… after Gateway proxy. Chat stream is an exception: same Beanstalk origin.",
    )
    add_table(
        doc,
        ["Group", "Method and path", "Auth", "What it does"],
        [
            ["Health", "GET /health", "None", "Beanstalk health check"],
            ["Auth", "GET /api/auth/me", "JWT", "Upsert profile; return role and settings"],
            ["Search", "GET /api/assets/search", "JWT", "CoinGecko or vnstock search"],
            ["Quote", "GET/POST /api/assets/{type}/{symbol}/quote[/refresh]", "JWT", "Cached quote; optional live refresh"],
            ["Watchlist", "GET/POST/DELETE /api/watchlist", "JWT", "User watchlist CRUD"],
            ["Holdings", "GET/POST/PUT/DELETE /api/holdings", "JWT", "Positions with qty and cost"],
            ["Portfolio", "GET /api/portfolio", "JWT", "Value, PnL, allocation JSON"],
            ["Refresh", "POST /api/portfolio/refresh", "JWT", "Force CoinGecko + vnstock"],
            ["Export", "GET /api/portfolio/export", "JWT", "CSV of the same valuation"],
            ["History", "GET /api/assets/{type}/{symbol}/history", "JWT", "S3 cache or live OHLCV"],
            ["News", "GET /api/news", "JWT", "Read news written by Lambda"],
            ["FX", "GET /api/fx/rates", "JWT", "Read stored rates only"],
            ["FX admin", "POST /api/admin/fx/refresh", "Admin", "Call ExchangeRate-API"],
            ["Admin", "GET/PUT /api/admin/settings", "Admin", "Jobs, TTL, chat model"],
            ["RSS", "CRUD /api/admin/rss-sources", "Admin", "Feeds for the news job"],
            ["Jobs", "GET /api/admin/job-runs; POST .../jobs/news/run", "Admin", "Status; manual news invoke"],
            ["Chat", "POST /api/chat/stream", "JWT", "SSE to OpenRouter; not Gateway"],
            ["Snapshots", "GET /api/snapshots[/{date}]", "JWT", "Read stored daily snapshots"],
        ],
    )
    add_caption(doc, "Table 11. FastAPI endpoints used by the client.")

    add_body(
        doc,
        "Third-party HTTP APIs called from adapters (never from the browser): CoinGecko REST, vnstock/broker HTTP, ExchangeRate-API Standard/Pair, OpenRouter chat completions, Gmail SMTP, and RSS GET on admin URLs. Google OAuth is handled inside Cognito, not in application code.",
    )

    # --- 6. References ---
    add_h1(doc, "6. References")
    refs = [
        "[1] CoinGecko, “API documentation.” [Online]. Available: https://www.coingecko.com/en/api/documentation",
        "[2] Amazon Web Services, “AWS Elastic Beanstalk Developer Guide.” [Online]. Available: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html",
        "[3] Amazon Web Services, “Amazon API Gateway Developer Guide — HTTP APIs.” [Online]. Available: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html",
        "[4] Amazon Web Services, “Amazon Cognito Developer Guide.” [Online]. Available: https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html",
        "[5] Amazon Web Services, “Amazon DynamoDB Developer Guide.” [Online]. Available: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html",
        "[6] Amazon Web Services, “Amazon S3 User Guide.” [Online]. Available: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
        "[7] Amazon Web Services, “Amazon Athena User Guide.” [Online]. Available: https://docs.aws.amazon.com/athena/latest/ug/what-is.html",
        "[8] Amazon Web Services, “Amazon EventBridge User Guide.” [Online]. Available: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html",
        "[9] Amazon Web Services, “AWS Lambda Developer Guide.” [Online]. Available: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
        "[10] T. Vu, “vnstock.” [Online]. Available: https://github.com/thinh-vu/vnstock",
        "[11] ExchangeRate-API, “API documentation.” [Online]. Available: https://www.exchangerate-api.com/docs/overview",
        "[12] Vercel, “Next.js documentation.” [Online]. Available: https://nextjs.org/docs",
        "[13] S. Ramírez, “FastAPI documentation.” [Online]. Available: https://fastapi.tiangolo.com/",
        "[14] OpenRouter, “API reference.” [Online]. Available: https://openrouter.ai/docs",
    ]
    for ref in refs:
        add_body(doc, ref, size=10, after=80)

    doc.core_properties.title = "OpenPortfo Solution Architecture"
    doc.core_properties.author = "Mai Gia Phu"
    doc.core_properties.subject = "RMIT Cloud Computing Assessment 3"
    doc.save(str(OUT))
    print("wrote", OUT, "size", OUT.stat().st_size)


if __name__ == "__main__":
    build()
