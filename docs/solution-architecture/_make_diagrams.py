"""Generate architecture PNGs for the OpenPortfo solution architecture document."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent / "doc_images"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#1F4E79"
BLUE = "#2E75B6"
ORANGE = "#ED7100"
PURPLE = "#8C4FFF"
MAGENTA = "#C925D1"
GREEN = "#7AA116"
PINK = "#E7157B"
DARK = "#232F3E"
TEXT = "#222222"
MUTED = "#555555"
BG = "#FFFFFF"
BOX_FILL = "#FFFFFF"
GROUP = "#F4F7FB"


def _fig(w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h), dpi=180)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    return fig, ax


def _group(ax, x, y, w, h, title, color):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.4,rounding_size=1.2",
            linewidth=1.2,
            edgecolor=color,
            facecolor=GROUP,
            linestyle="-",
        )
    )
    ax.text(
        x + 1.2,
        y + h - 3.2,
        title,
        fontsize=9,
        fontweight="bold",
        color=color,
        fontfamily="Arial",
        ha="left",
        va="center",
    )


def _box(ax, x, y, w, h, title, subtitle, color):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.25,rounding_size=0.8",
            linewidth=1.4,
            edgecolor=color,
            facecolor=BOX_FILL,
        )
    )
    ax.add_patch(Rectangle((x, y), 0.7, h, facecolor=color, edgecolor="none"))
    ax.text(
        x + w / 2 + 0.2,
        y + h * 0.62,
        title,
        fontsize=8,
        fontweight="bold",
        color=DARK,
        fontfamily="Arial",
        ha="center",
        va="center",
        wrap=True,
    )
    if subtitle:
        ax.text(
            x + w / 2 + 0.2,
            y + h * 0.28,
            subtitle,
            fontsize=6.4,
            color=MUTED,
            fontfamily="Arial",
            ha="center",
            va="center",
            linespacing=1.15,
        )


def _arrow(ax, x1, y1, x2, y2, label="", color=DARK, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.15,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 1.6,
            label,
            fontsize=6.2,
            color=color,
            fontfamily="Arial",
            ha="center",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.92),
        )


def _caption(ax, text):
    ax.text(50, 1.8, text, fontsize=7, color=MUTED, fontfamily="Arial", ha="center")


def fig1_high_level():
    fig, ax = _fig(13.4, 8.8)

    ax.text(
        50,
        97.6,
        "Figure 1. OpenPortfo high-level architecture",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    # Layer 1 — client
    _box(ax, 42, 84, 16, 10, "User / browser", "Next.js CSR pages", NAVY)

    # Layer 2 — edge / compute
    _box(ax, 3, 66, 18, 12, "Amazon Cognito", "Sign-in and JWT", BLUE)
    _box(ax, 27, 66, 20, 12, "API Gateway", "HTTP proxy /api/*", PURPLE)
    _box(ax, 53, 66, 22, 12, "Elastic Beanstalk", "UI files + FastAPI", ORANGE)
    _box(ax, 79, 66, 18, 12, "EventBridge", "Daily cron rules", PINK)

    # Layer 3 — data + jobs
    _box(ax, 3, 44, 18, 14, "DynamoDB", "App records\nand price cache", MAGENTA)
    _box(ax, 25, 44, 16, 14, "S3", "History and\nsnapshot files", GREEN)
    _box(ax, 45, 44, 16, 14, "Athena", "SQL on\nsnapshots/", PURPLE)
    _box(ax, 65, 44, 16, 14, "Lambda", "Four scheduled\njobs", ORANGE)
    _box(ax, 84, 44, 13, 14, "Email", "SES or SMTP", GREEN)

    # Layer 4 — external
    _box(ax, 3, 18, 14, 16, "CoinGecko", "Crypto prices", GREEN)
    _box(ax, 20, 18, 14, 16, "vnstock", "VN stocks", GREEN)
    _box(ax, 37, 18, 14, 16, "RSS", "Market news", GREEN)
    _box(ax, 54, 18, 14, 16, "ExchangeRate-API", "USD / VND", GREEN)
    _box(ax, 71, 18, 12, 16, "OpenRouter", "Chat LLM", GREEN)

    # Only adjacent, non-crossing arrows. Detailed invoke paths are in Figures 2–4.
    _arrow(ax, 46, 84, 12, 78, "login", BLUE)
    _arrow(ax, 50, 84, 37, 78, "REST", PURPLE)
    _arrow(ax, 54, 84, 64, 78, "UI + chat", ORANGE)
    _arrow(ax, 47, 72, 53, 72, "proxy", PURPLE)
    _arrow(ax, 88, 66, 73, 58, "cron", PINK)
    _arrow(ax, 64, 66, 12, 58, "", MAGENTA)
    _arrow(ax, 64, 66, 33, 58, "", GREEN)
    _arrow(ax, 73, 44, 44, 34, "jobs", GREEN)

    ax.text(
        50,
        12.5,
        "Request path: Browser → Cognito (login) and Beanstalk (UI). REST /api/* → API Gateway → FastAPI → DynamoDB/S3, and CoinGecko/vnstock on cache miss.",
        fontsize=6.7,
        ha="center",
        color=TEXT,
        fontfamily="Arial",
    )
    ax.text(
        50,
        9.6,
        "Schedule path: EventBridge → Lambda → RSS / market APIs / DynamoDB / S3 / email. Athena reads snapshot files later. Chat SSE stays on Beanstalk (not Gateway).",
        fontsize=6.7,
        ha="center",
        color=TEXT,
        fontfamily="Arial",
    )
    _caption(ax, "AWS Academy blocks CloudFront, so the live demo serves the UI from Elastic Beanstalk. REST still uses API Gateway.")
    fig.savefig(OUT / "fig1_high_level.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def fig2_client_ops():
    fig, ax = _fig(13.2, 8.6)
    ax.text(
        50,
        97.2,
        "Figure 2. How each client operation invokes the rest of the system",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    headers = ["UI action", "Entry", "Then", "Stores / providers"]
    xs = [3, 24, 48, 74]
    widths = [20, 22, 24, 23]
    ax.add_patch(Rectangle((2, 88.5), 96, 5.2, facecolor=NAVY, edgecolor=NAVY))
    for x, h in zip(xs, headers):
        ax.text(x + 1, 91, h, fontsize=8, fontweight="bold", color="white", fontfamily="Arial", va="center")

    rows = [
        ("Open site / click pages", "EB static files", "Browser renders Next.js CSR", "No AWS write"),
        ("Sign in / Sign up / Google", "Cognito Hosted UI", "Callback → ID token on later calls", "Cognito; DynamoDB profile"),
        ("Search assets", "Gateway → FastAPI", "GET /api/assets/search", "CoinGecko or vnstock"),
        ("Add / edit holding or watchlist", "Gateway → FastAPI", "POST/PUT/DELETE holdings or watchlist", "DynamoDB"),
        ("Open portfolio dashboard", "Gateway → FastAPI", "GET /api/portfolio (cache first)", "DynamoDB + PriceCache"),
        ("Click Refresh prices", "Gateway → FastAPI", "POST /api/portfolio/refresh", "CoinGecko + vnstock → cache"),
        ("Open history chart", "Gateway → FastAPI", "GET /api/assets/.../history", "S3 cache or live fetch"),
        ("Read news", "Gateway → FastAPI", "GET /api/news (read only)", "DynamoDB News (filled by Lambda)"),
        ("Ask chatbot", "EB same-origin SSE", "POST /api/chat/stream (not Gateway)", "OpenRouter; DynamoDB idempotency"),
        ("Admin: RSS, jobs, FX refresh", "Gateway → FastAPI", "Admin APIs; FX calls ExchangeRate-API", "DynamoDB settings / FX"),
        ("Export CSV", "Gateway → FastAPI", "GET /api/portfolio/export", "Same valuation as dashboard"),
    ]

    y = 83.2
    for i, (a, b, c, d) in enumerate(rows):
        fill = "#FFFFFF" if i % 2 == 0 else "#EEF3F8"
        ax.add_patch(Rectangle((2, y - 2.6), 96, 6.4, facecolor=fill, edgecolor="#D0D7DE", linewidth=0.6))
        vals = [a, b, c, d]
        for x, val in zip(xs, vals):
            ax.text(x + 1, y + 0.5, val, fontsize=6.6, color=TEXT, fontfamily="Arial", va="center")
        y -= 6.6

    _caption(ax, "Gateway timeout is 30s, so chat streaming stays on the Beanstalk origin. Lambda is never called by the browser.")
    fig.savefig(OUT / "fig2_client_operations.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def fig3_portfolio_seq():
    fig, ax = _fig(13.2, 8.2)
    ax.text(
        50,
        97,
        "Figure 3. Sequence: view portfolio and refresh prices",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    actors = [
        (8, "Browser"),
        (26, "API Gateway"),
        (46, "FastAPI\n(Beanstalk)"),
        (66, "DynamoDB"),
        (84, "CoinGecko\n/ vnstock"),
    ]
    for x, name in actors:
        ax.add_patch(FancyBboxPatch((x - 7, 86), 14, 8, boxstyle="round,pad=0.2", edgecolor=NAVY, facecolor="white", linewidth=1.3))
        ax.text(x, 90, name, fontsize=7.2, fontweight="bold", ha="center", va="center", fontfamily="Arial", color=DARK)
        ax.plot([x, x], [12, 86], color="#C5CDD6", linewidth=1)

    steps = [
        (80, "1. GET /api/portfolio  (Bearer Cognito JWT)", 8, 26),
        (73, "2. HTTP_PROXY to FastAPI", 26, 46),
        (66, "3. Verify JWT (Cognito JWKS), load holdings", 46, 66),
        (59, "4. Read PriceCache (+ stored FX rates)", 46, 66),
        (52, "5. If cache miss: fetch live quotes", 46, 84),
        (45, "6. Write last good prices back to cache", 46, 66),
        (38, "7. Compute value, cost, PnL, allocation JSON", 46, 46),
        (31, "8. JSON response for tables and pie chart", 46, 8),
        (22, "9. Refresh: POST /api/portfolio/refresh (same Gateway path)", 8, 26),
        (15, "10. FastAPI force-fetches CoinGecko + vnstock, then same JSON", 46, 84),
    ]
    for y, label, x1, x2 in steps:
        ax.annotate(
            "",
            xy=(x2, y),
            xytext=(x1, y),
            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.1),
        )
        ax.text(50, y + 1.5, label, fontsize=6.8, ha="center", fontfamily="Arial", color=TEXT)

    ax.text(
        50,
        7.5,
        "FX is not fetched on this path. Portfolio conversion uses the last admin-refreshed rates in DynamoDB.",
        fontsize=7,
        ha="center",
        color=MUTED,
        fontfamily="Arial",
    )
    fig.savefig(OUT / "fig3_portfolio_sequence.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def fig4_jobs():
    fig, ax = _fig(13.2, 8.0)
    ax.text(
        50,
        97,
        "Figure 4. Scheduled path: EventBridge → Lambda (no browser traffic)",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    _box(ax, 4, 72, 18, 16, "EventBridge", "cron(0 17 * * ? *)\nnews, price, snapshot\ncron(15 17 * * ? *) email", PINK)
    _box(ax, 32, 72, 18, 16, "Lambda\nopenportfo-jobs", "handler reads event.job\nnews | price | snapshot | email", ORANGE)

    _box(ax, 4, 38, 20, 22, "News job", "Fetch admin RSS URLs\nkeyword / symbol match\nwrite News + JobRuns", BLUE)
    _box(ax, 28, 38, 20, 22, "Price job", "Batch quotes for known\nsymbols → PriceCache\n(+ history to S3)", ORANGE)
    _box(ax, 52, 38, 20, 22, "Snapshot job", "Per-user valuation\nDynamoDB SNAP#date\nS3 snapshots/userId=…/dt=", MAGENTA)
    _box(ax, 76, 38, 20, 22, "Email job", "Opt-in users only\nPnL + holdings + news\nSES or Gmail SMTP", GREEN)

    _box(ax, 10, 8, 18, 18, "RSS feeds", "CafeF / market RSS\nfrom Admin list", GREEN)
    _box(ax, 34, 8, 18, 18, "Market APIs", "CoinGecko + vnstock", GREEN)
    _box(ax, 58, 8, 18, 18, "DynamoDB + S3", "News, cache, snapshots", MAGENTA)
    _box(ax, 82, 8, 14, 18, "Athena", "SQL later on S3\nsnapshot files", PURPLE)

    _arrow(ax, 22, 80, 32, 80, "invoke", PINK)
    _arrow(ax, 41, 72, 14, 60, "", ORANGE)
    _arrow(ax, 41, 72, 38, 60, "", ORANGE)
    _arrow(ax, 41, 72, 62, 60, "", ORANGE)
    _arrow(ax, 41, 72, 86, 60, "", ORANGE)
    _arrow(ax, 14, 38, 19, 26, "fetch", GREEN)
    _arrow(ax, 38, 38, 43, 26, "fetch", GREEN)
    _arrow(ax, 62, 38, 67, 26, "write", MAGENTA)
    _arrow(ax, 67, 17, 82, 17, "query", PURPLE)

    _caption(ax, "Admin can also run the news job from the UI (FastAPI → Lambda invoke). Daily cron still owns the unattended path.")
    fig.savefig(OUT / "fig4_scheduled_jobs.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def fig5_data():
    fig, ax = _fig(13.2, 8.4)
    ax.text(
        50,
        97.2,
        "Figure 5. Data stores: DynamoDB tables and S3 layout",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    tables = [
        ("users", "PK userId\nemail, role, keywords,\nemailOptIn, currency"),
        ("holdings", "PK userId  SK HOLD#type#symbol\nqty, avgCost, currency"),
        ("watchlist", "PK userId  SK WATCH#type#symbol\naddedAt"),
        ("price-cache", "PK type#symbol\nprice, asOf, ttl"),
        ("news", "PK date  SK source#hash\ntitle, url, symbols"),
        ("snapshots", "PK userId  SK SNAP#date\ntotals, lines, fx"),
        ("settings", "PK SETTINGS SK GLOBAL\njobs, cache TTL, chat"),
        ("fx", "PK FX  SK LATEST\nrates, asOf, status"),
        ("rss", "PK RSS  SK sourceId\nname, url, enabled"),
        ("job-runs", "PK JOB#type  SK runAt\nstatus, counts"),
        ("chat-idempotency", "PK userId  SK requestId\nTTL expiresAt"),
    ]
    x0, y0 = 3.5, 78
    for i, (name, keys) in enumerate(tables):
        col, row = i % 4, i // 4
        x = x0 + col * 24.2
        y = y0 - row * 22
        _box(ax, x, y, 22.5, 18, name, keys, MAGENTA)

    _box(
        ax,
        3.5,
        6,
        93,
        16,
        "S3 data bucket  (not the website bucket)",
        "snapshots/userId={id}/dt={YYYY-MM-DD}/part.json     history/{crypto|stock}/{id}/{range}.json     athena-results/\nAthena table openportfo.portfolio_snapshots_raw reads the snapshots/ prefix with JSON SerDe.",
        GREEN,
    )
    fig.savefig(OUT / "fig5_data_model.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def fig6_login_chat():
    fig, ax = _fig(13.2, 8.2)
    ax.text(
        50,
        97,
        "Figure 6. Login (Cognito) and chatbot (SSE) — two different entry points",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        fontfamily="Arial",
        ha="center",
    )

    _group(ax, 2, 50, 96, 42, "A. Sign in", BLUE)
    _box(ax, 4, 62, 14, 22, "Browser", "Click Sign in", NAVY)
    _box(ax, 22, 62, 16, 22, "Cognito\nHosted UI", "Email or Google\nOAuth code", BLUE)
    _box(ax, 42, 62, 16, 22, "Browser\ncallback", "Stores ID token", NAVY)
    _box(ax, 62, 62, 16, 22, "Gateway +\nFastAPI", "GET /api/auth/me\nJWKS verify", ORANGE)
    _box(ax, 82, 62, 14, 22, "DynamoDB\nusers", "Create profile\nif missing", MAGENTA)
    _arrow(ax, 18, 73, 22, 73, "redirect", BLUE)
    _arrow(ax, 38, 73, 42, 73, "code", BLUE)
    _arrow(ax, 58, 73, 62, 73, "Bearer", ORANGE)
    _arrow(ax, 78, 73, 82, 73, "upsert", MAGENTA)

    _group(ax, 2, 6, 96, 40, "B. Chat (not API Gateway — 30s timeout is too short for SSE)", ORANGE)
    _box(ax, 4, 14, 16, 22, "Browser\nchat bubble", "POST /api/chat/stream\nsame EB origin", NAVY)
    _box(ax, 26, 14, 18, 22, "FastAPI on EB", "Auth + session cap\nidempotency check", ORANGE)
    _box(ax, 50, 14, 18, 22, "OpenRouter", "Free LLM models\nserver-side only", GREEN)
    _box(ax, 74, 14, 20, 22, "DynamoDB", "chat-idempotency\nTTL; no chat log store", MAGENTA)
    _arrow(ax, 20, 25, 26, 25, "SSE", ORANGE)
    _arrow(ax, 44, 25, 50, 25, "prompt", GREEN)
    _arrow(ax, 44, 20, 74, 25, "requestId", MAGENTA)

    fig.savefig(OUT / "fig6_login_and_chat.png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    # Figures 1, 3, 4, 6 are AWS-icon HTML screenshots under doc_images/_icons/.
    fig2_client_ops()
    print("wrote", list(OUT.glob("*.png")))
