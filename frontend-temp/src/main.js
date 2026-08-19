/**
 * OpenPortfo temp viewer — vanilla JS against local FastAPI.
 * Auth: paste Bearer token (fake:<userId> or Cognito JWT) into sessionStorage.
 */

const TOKEN_KEY = "openportfo_token";
const API_KEY = "openportfo_api";

const $ = (id) => document.getElementById(id);

function getApiBase() {
  return ($("apiUrl").value || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function getToken() {
  return ($("token").value || "").trim();
}

function saveAuth() {
  sessionStorage.setItem(TOKEN_KEY, getToken());
  sessionStorage.setItem(API_KEY, getApiBase());
  updateAuthPill();
  if (typeof chatHistory !== "undefined") {
    chatHistory.length = 0;
    if ($("chatLog")) renderChatLog();
  }
}

function loadAuth() {
  const api = sessionStorage.getItem(API_KEY) || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const token = sessionStorage.getItem(TOKEN_KEY) || "";
  $("apiUrl").value = api;
  $("token").value = token;
  updateAuthPill();
}

function updateAuthPill() {
  const t = getToken();
  const el = $("authStatus");
  if (!t) {
    el.textContent = "no token";
    el.classList.remove("ok");
  } else {
    el.textContent = t.startsWith("fake:") ? t : "token set";
    el.classList.add("ok");
  }
}

function show(el, data) {
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${getApiBase()}${path}`, { ...options, headers });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

function switchTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `tab-${name}`);
  });
}

function renderPortfolio(data) {
  const host = $("portfolioTable");
  const klass = $("portfolioClass");
  const classes = data?.totalsByAssetClass || {};
  const classKeys = Object.keys(classes);
  klass.innerHTML = classKeys.length
    ? `<div class="stat-grid">${classKeys
        .map((key) => {
          const row = classes[key];
          return `<div class="stat"><span>${escapeHtml(key)}</span><strong>${escapeHtml(
            formatMoney(row.marketValue, row.currency)
          )}</strong><span class="muted">PnL ${escapeHtml(row.pnl ?? "—")}</span></div>`;
        })
        .join("")}</div>`
    : "";
  const lines = data?.lines || [];
  if (!lines.length) {
    host.innerHTML = "<p class='muted'>No lines</p>";
    return;
  }
  const rows = lines
    .map(
      (l) => `<tr>
      <td>${escapeHtml(l.assetType || "")}</td>
      <td><button type="button" class="clickable asset-link" data-type="${escapeHtml(
        l.assetType || ""
      )}" data-slug="${escapeHtml(l.symbol || "")}">${escapeHtml(l.symbol || "")}</button></td>
      <td>${escapeHtml(l.qty ?? "")}</td>
      <td>${escapeHtml(l.price ?? "—")}</td>
      <td>${escapeHtml(l.marketValue ?? "—")}</td>
      <td>${escapeHtml(l.pnl ?? "—")}</td>
      <td>${escapeHtml(l.currency || "")}</td>
      <td>${l.stale ? "stale" : ""}</td>
      <td>${l.missingPrice ? "yes" : ""}</td>
    </tr>`
    )
    .join("");
  host.innerHTML = `<table>
    <thead><tr>
      <th>Type</th><th>Symbol</th><th>Qty</th><th>Price</th>
      <th>MV</th><th>PnL</th><th>CCY</th><th>Stale</th><th>Missing</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>
  <p class="muted">totalsDisplay: ${escapeHtml(JSON.stringify(data.totalsDisplay))} · fx: ${escapeHtml(data.fx?.status)}</p>`;
}

function renderWatchlist(items) {
  const host = $("watchTable");
  if (!Array.isArray(items) || !items.length) {
    host.innerHTML = "<p class='muted'>No watchlist items</p>";
    return;
  }
  host.innerHTML = `<table>
    <thead><tr><th>Type</th><th>Symbol</th><th>Price</th><th>CCY</th><th>Stale</th><th>As of</th></tr></thead>
    <tbody>${items
      .map(
        (item) => `<tr>
        <td>${escapeHtml(item.assetType || "")}</td>
        <td><button type="button" class="clickable asset-link" data-type="${escapeHtml(
          item.assetType || ""
        )}" data-slug="${escapeHtml(item.symbol || "")}">${escapeHtml(item.symbol || "")}</button></td>
        <td>${escapeHtml(item.price != null ? formatMoney(item.price, item.currency) : "—")}</td>
        <td>${escapeHtml(item.currency || "")}</td>
        <td>${item.stale ? "yes" : ""}</td>
        <td>${escapeHtml(item.asOf ? new Date(item.asOf).toLocaleString() : "")}</td>
      </tr>`
      )
      .join("")}</tbody>
  </table>`;
}

function renderNews(items) {
  const ul = $("newsList");
  if (!Array.isArray(items) || !items.length) {
    ul.innerHTML = "<li class='muted'>No items</li>";
    return;
  }
  ul.innerHTML = items
    .map(
      (n) =>
        `<li><a href="${n.url || "#"}" target="_blank" rel="noreferrer">${escapeHtml(
          n.title || "(no title)"
        )}</a> <span class="muted">${escapeHtml(n.source || "")}</span></li>`
    )
    .join("");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMoney(value, currency) {
  const number = Number(value);
  if (!Number.isFinite(number)) return `${value ?? "—"} ${currency || ""}`.trim();
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: currency === "VND" ? 0 : 8,
    }).format(number);
  } catch {
    return `${number.toLocaleString()} ${currency || ""}`.trim();
  }
}

function selectedMarketAsset() {
  const value = $("marketResults").value || $("marketPopular").value;
  const [assetType, symbol, assetId] = value.split("|");
  return { assetType, symbol, assetId };
}

function drawChart(host, points, { valueKey = "priceDisplay", fallbackKey = "price" } = {}) {
  const series = (points || [])
    .map((p) => ({ t: p.t, v: Number(p[valueKey] ?? p[fallbackKey]) }))
    .filter((p) => Number.isFinite(p.v));
  if (!series.length) {
    host.innerHTML = "<p class='muted'>No chart points</p>";
    return;
  }
  const w = 720;
  const h = 220;
  const pad = 28;
  const min = Math.min(...series.map((p) => p.v));
  const max = Math.max(...series.map((p) => p.v));
  const span = max - min || 1;
  const coords = series
    .map((p, i) => {
      const x = pad + (i / Math.max(series.length - 1, 1)) * (w - pad * 2);
      const y = h - pad - ((p.v - min) / span) * (h - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");
  const first = series[0].t ? new Date(series[0].t).toLocaleDateString() : "";
  const last = series[series.length - 1].t ? new Date(series[series.length - 1].t).toLocaleDateString() : "";
  host.innerHTML = `<svg viewBox="0 0 ${w} ${h}" class="chart" role="img" aria-label="Price chart">
    <polyline points="${coords}"></polyline>
  </svg>
  <p class="muted">${escapeHtml(first)} → ${escapeHtml(last)} · ${series.length} points · min ${escapeHtml(
    String(min)
  )} · max ${escapeHtml(String(max))}</p>`;
}

function assetQuery() {
  return {
    type: $("assetType").value,
    slug: $("assetSlug").value.trim(),
    currency: $("assetCurrency").value,
    range: $("assetRange").value,
  };
}

function writeAssetHash({ type, slug, currency, range }) {
  const params = new URLSearchParams();
  if (currency) params.set("currency", currency);
  if (range) params.set("range", range);
  const q = params.toString();
  const next = `#/${type}/${encodeURIComponent(slug)}${q ? `?${q}` : ""}`;
  if (location.hash !== next) history.replaceState(null, "", next);
}

function parseAssetHash() {
  const raw = location.hash.replace(/^#/, "");
  const match = raw.match(/^\/(crypto|stock)\/([^?]+)/i);
  if (!match) return null;
  const params = new URLSearchParams(raw.split("?")[1] || "");
  return {
    type: match[1].toLowerCase(),
    slug: decodeURIComponent(match[2]),
    currency: params.get("currency") || "",
    range: params.get("range") || "30d",
  };
}

function applyAssetForm(q) {
  if (!q) return;
  $("assetType").value = q.type;
  $("assetSlug").value = q.slug;
  if ([...$("assetCurrency").options].some((o) => o.value === q.currency)) {
    $("assetCurrency").value = q.currency;
  }
  if ([...$("assetRange").options].some((o) => o.value === q.range)) {
    $("assetRange").value = q.range;
  }
}

function renderAssetDetail(data) {
  const hero = $("assetHero");
  const stats = $("assetStats");
  const profile = data.profile || {};
  const quote = data.quote || {};
  const links = Object.entries(profile.links || {}).filter(([, url]) => url);
  hero.classList.remove("muted");
  hero.innerHTML = `
    ${profile.imageUrl ? `<img src="${escapeHtml(profile.imageUrl)}" alt="" />` : "<div></div>"}
    <div>
      <span class="eyebrow">${escapeHtml(data.assetType)} · ${escapeHtml(data.nativeCurrency)} → ${escapeHtml(
        data.displayCurrency
      )}</span>
      <h3 style="margin:0.15rem 0">${escapeHtml(data.name || "")} <span class="muted">${escapeHtml(
        data.symbol || ""
      )}</span></h3>
      <div class="price">${escapeHtml(
        formatMoney(quote.priceDisplay || quote.price, data.displayCurrency || quote.currency)
      )}</div>
      <p class="muted">Native ${escapeHtml(formatMoney(quote.price, quote.currency))} · fx ${escapeHtml(
        data.fx?.status || "—"
      )} ${quote.stale ? "· stale" : ""} · ${escapeHtml(data.assetId || "")}</p>
      <p class="desc">${escapeHtml(profile.description || "No description")}</p>
      <div class="link-row">${links
        .map(([name, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(name)}</a>`)
        .join("")}</div>
    </div>`;
  const cells = [
    ["24h %", quote.changePercent24h],
    ["7d %", quote.changePercent7d],
    ["30d %", quote.changePercent30d],
    ["Market cap", quote.marketCapDisplay || quote.marketCap],
    ["Volume 24h", quote.volume24hDisplay || quote.volume24h],
    ["High 24h", quote.high24hDisplay || quote.high24h],
    ["Low 24h", quote.low24hDisplay || quote.low24h],
    ["Rank", profile.marketCapRank],
    ["Exchange", profile.exchange],
    ["Industry", profile.industry],
    ["Circulating", profile.circulatingSupply],
    ["Max supply", profile.maxSupply],
  ].filter(([, v]) => v != null && v !== "");
  stats.innerHTML = cells.length
    ? `<div class="stat-grid">${cells
        .map(([label, value]) => `<div class="stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
        .join("")}</div>`
    : "";
  drawChart($("assetChart"), data.history?.points || [], {
    valueKey: data.fx?.rate ? "priceDisplay" : "price",
  });
}

function openAssetDetail({ type, slug, currency, range }) {
  applyAssetForm({
    type,
    slug,
    currency: currency ?? $("assetCurrency").value,
    range: range ?? $("assetRange").value,
  });
  switchTab("asset");
  return loadAssetDetail();
}

async function loadAssetDetail() {
  const q = assetQuery();
  if (!q.slug) {
    show($("outAsset"), { error: "Enter a slug such as btc or VNM" });
    return;
  }
  const params = new URLSearchParams();
  if (q.currency) params.set("currency", q.currency);
  if (q.range) params.set("range", q.range);
  writeAssetHash(q);
  try {
    const data = await api(
      `/api/assets/${encodeURIComponent(q.type)}/${encodeURIComponent(q.slug)}?${params}`
    );
    renderAssetDetail(data);
    show($("outAsset"), data);
  } catch (e) {
    show($("outAsset"), { error: e.message, body: e.body });
  }
}

async function loadAssetHistoryOnly() {
  const q = assetQuery();
  if (!q.slug) return;
  const params = new URLSearchParams({ range: q.range });
  if (q.currency) params.set("currency", q.currency);
  writeAssetHash(q);
  try {
    const data = await api(
      `/api/assets/${encodeURIComponent(q.type)}/${encodeURIComponent(q.slug)}/history?${params}`
    );
    drawChart($("assetChart"), data.points || [], {
      valueKey: data.fx?.rate ? "priceDisplay" : "price",
    });
    show($("outAsset"), data);
  } catch (e) {
    show($("outAsset"), { error: e.message, body: e.body });
  }
}

function renderQuote(quote) {
  $("marketPriceCard").classList.remove("muted");
  $("marketPriceCard").innerHTML = `
    <span class="eyebrow">${escapeHtml(quote.assetType)}</span>
    <strong>${escapeHtml(quote.symbol)}</strong>
    <span class="price">${escapeHtml(formatMoney(quote.price, quote.currency))}</span>
    <span class="muted">As of ${escapeHtml(new Date(quote.asOf).toLocaleString())} · ${escapeHtml(quote.source)}</span>`;
}

async function loadMarketQuote(force = false) {
  const { assetType, symbol, assetId } = selectedMarketAsset();
  if (!assetType || !symbol) return;
  const path = `/api/assets/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol)}/quote${
    force ? "/refresh" : ""
  }?assetId=${encodeURIComponent(assetId || "")}`;
  try {
    const quote = await api(path, force ? { method: "POST" } : {});
    renderQuote(quote);
    show($("outMarket"), quote);
  } catch (e) {
    show($("outMarket"), { error: e.message, body: e.body });
  }
}

function renderDynamoTables(data) {
  const tables = data?.tables || [];
  const select = $("dynamoTable");
  const selected = select.value;
  select.innerHTML = `<option value="">Select a table</option>${tables
    .map((table) => `<option value="${escapeHtml(table.name)}">${escapeHtml(table.name)}</option>`)
    .join("")}`;
  if (tables.some((table) => table.name === selected)) select.value = selected;
  $("dynamoSummary").innerHTML = `
    <p class="muted">Endpoint: ${escapeHtml(data.endpoint || "")} · Region: ${escapeHtml(data.region || "")}</p>
    <table>
      <thead><tr><th>Table</th><th>Status</th><th>Approx. items</th><th>Keys</th></tr></thead>
      <tbody>${tables
        .map((table) => `<tr>
          <td>${escapeHtml(table.name)}</td>
          <td>${escapeHtml(table.status)}</td>
          <td>${table.itemCount ?? 0}</td>
          <td>${escapeHtml((table.keySchema || []).map((key) => `${key.AttributeName} (${key.KeyType})`).join(", "))}</td>
        </tr>`)
        .join("")}</tbody>
    </table>`;
}

// ---- wire events ----

$("btnSaveAuth").onclick = saveAuth;

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (btn) {
    switchTab(btn.dataset.tab);
    if (btn.dataset.tab === "chat") loadChatModels();
  }
});

$("btnHealth").onclick = async () => {
  try {
    show($("outHealth"), await api("/health"));
  } catch (e) {
    show($("outHealth"), { error: e.message, body: e.body });
  }
};

$("btnReady").onclick = async () => {
  try {
    show($("outHealth"), await api("/health/ready"));
  } catch (e) {
    show($("outHealth"), { error: e.message, status: e.status, body: e.body });
  }
};

$("btnMe").onclick = async () => {
  try {
    const me = await api("/api/auth/me");
    show($("outMe"), me);
    if (me.newsKeywords) $("setKeywords").value = (me.newsKeywords || []).join(", ");
    if (me.preferredCurrency) $("setCurrency").value = me.preferredCurrency;
    $("setEmailOptIn").checked = !!me.emailOptIn;
  } catch (e) {
    show($("outMe"), { error: e.message, body: e.body });
  }
};

$("btnMakeAdmin").onclick = async () => {
  try {
    const me = await api("/api/debug/auth/make-admin", { method: "POST" });
    show($("outMe"), me);
    const el = $("authStatus");
    el.textContent = `${getToken().startsWith("fake:") ? getToken() : "token set"} · admin`;
    el.classList.add("ok");
  } catch (e) {
    show($("outMe"), { error: e.message, body: e.body });
  }
};

$("btnSettingsGet").onclick = async () => {
  try {
    const settings = await api("/api/settings");
    show($("outSettings"), settings);
    if (settings.newsKeywords) $("setKeywords").value = (settings.newsKeywords || []).join(", ");
    if (settings.preferredCurrency) $("setCurrency").value = settings.preferredCurrency;
    $("setEmailOptIn").checked = !!settings.emailOptIn;
  } catch (e) {
    show($("outSettings"), { error: e.message, body: e.body });
  }
};

$("btnSettings").onclick = async () => {
  try {
    const keywords = $("setKeywords").value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const body = {
      newsKeywords: keywords,
      emailOptIn: $("setEmailOptIn").checked,
    };
    const cur = $("setCurrency").value.trim();
    if (cur) body.preferredCurrency = cur;
    show($("outSettings"), await api("/api/settings", { method: "PUT", body: JSON.stringify(body) }));
  } catch (e) {
    show($("outSettings"), { error: e.message, body: e.body });
  }
};

$("btnHoldingsList").onclick = async () => {
  try {
    show($("outHoldings"), await api("/api/holdings"));
  } catch (e) {
    show($("outHoldings"), { error: e.message, body: e.body });
  }
};

$("btnHoldingAdd").onclick = async () => {
  try {
    const body = {
      assetType: $("hType").value,
      symbol: $("hSymbol").value.trim(),
      assetId: $("hAssetId").value.trim() || null,
      qty: $("hQty").value.trim(),
      avgCost: $("hAvg").value.trim(),
      currency: $("hCur").value.trim() || "USD",
    };
    show(
      $("outHoldings"),
      await api("/api/holdings", { method: "POST", body: JSON.stringify(body) })
    );
  } catch (e) {
    show($("outHoldings"), { error: e.message, body: e.body });
  }
};

$("btnHoldingsExport").onclick = async () => {
  try {
    const headers = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${getApiBase()}/api/holdings/export`, { headers });
    if (!res.ok) {
      const body = await res.text();
      throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, body });
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "holdings.csv";
    a.click();
    URL.revokeObjectURL(url);
    show($("outHoldings"), { downloaded: "holdings.csv" });
  } catch (e) {
    show($("outHoldings"), { error: e.message, body: e.body });
  }
};

$("btnHoldingDel").onclick = async () => {
  try {
    const t = $("hType").value;
    const s = $("hSymbol").value.trim();
    await api(`/api/holdings/${encodeURIComponent(t)}/${encodeURIComponent(s)}`, {
      method: "DELETE",
    });
    show($("outHoldings"), { deleted: `${t}/${s}` });
  } catch (e) {
    show($("outHoldings"), { error: e.message, body: e.body });
  }
};

$("btnWatchList").onclick = async () => {
  try {
    const items = await api("/api/watchlist");
    renderWatchlist(items);
    show($("outWatch"), items);
  } catch (e) {
    show($("outWatch"), { error: e.message, body: e.body });
  }
};

$("btnWatchAdd").onclick = async () => {
  try {
    const body = {
      assetType: $("wType").value,
      symbol: $("wSymbol").value.trim(),
      assetId: $("wAssetId").value.trim() || null,
    };
    show(
      $("outWatch"),
      await api("/api/watchlist", { method: "POST", body: JSON.stringify(body) })
    );
  } catch (e) {
    show($("outWatch"), { error: e.message, body: e.body });
  }
};

$("btnWatchDel").onclick = async () => {
  try {
    const t = $("wType").value;
    const s = $("wSymbol").value.trim();
    await api(`/api/watchlist/${encodeURIComponent(t)}/${encodeURIComponent(s)}`, {
      method: "DELETE",
    });
    show($("outWatch"), { deleted: `${t}/${s}` });
  } catch (e) {
    show($("outWatch"), { error: e.message, body: e.body });
  }
};

async function loadPortfolio(refresh = false) {
  const params = new URLSearchParams();
  const d = $("pDisplay").value.trim();
  const t = $("pType").value;
  if (d) params.set("displayCurrency", d);
  if (t) params.set("assetType", t);
  const q = params.toString() ? `?${params}` : "";
  try {
    const data = refresh
      ? await api(`/api/portfolio/refresh${q}`, { method: "POST" })
      : await api(`/api/portfolio${q}`);
    renderPortfolio(data);
    show($("outPortfolio"), data);
  } catch (e) {
    show($("outPortfolio"), { error: e.message, body: e.body });
  }
}

$("btnPortfolio").onclick = () => loadPortfolio(false);
$("btnPortfolioRefresh").onclick = () => loadPortfolio(true);

$("btnPerformance").onclick = async () => {
  const range = $("pPerfRange").value;
  try {
    const data = await api(`/api/portfolio/performance?range=${encodeURIComponent(range)}`);
    drawChart($("perfChart"), data.points || [], { valueKey: "marketValue", fallbackKey: "marketValue" });
    show($("outPortfolio"), data);
  } catch (e) {
    show($("outPortfolio"), { error: e.message, body: e.body });
  }
};

$("btnAssetLoad").onclick = () => loadAssetDetail();
$("btnAssetHistory").onclick = () => loadAssetHistoryOnly();
$("assetRange").onchange = () => {
  if ($("tab-asset").classList.contains("active") && $("assetSlug").value.trim()) {
    loadAssetHistoryOnly();
  }
};

document.body.addEventListener("click", (e) => {
  const link = e.target.closest(".asset-link");
  if (!link) return;
  openAssetDetail({
    type: link.dataset.type,
    slug: link.dataset.slug,
    currency: $("assetCurrency").value,
    range: $("assetRange").value,
  });
});

$("btnFxGet").onclick = async () => {
  try {
    show($("outFx"), await api("/api/fx/rates"));
  } catch (e) {
    show($("outFx"), { error: e.message, body: e.body });
  }
};

$("btnFxRefresh").onclick = async () => {
  try {
    show($("outFx"), await api("/api/admin/fx/refresh", { method: "POST" }));
  } catch (e) {
    // 502 keeps previous rates in body.rates
    show($("outFx"), {
      error: e.message,
      status: e.status,
      body: e.body,
      note: "On 502, previous rates remain in body.rates (S06)",
    });
  }
};

$("btnFxSwap").onclick = () => {
  const source = $("fxSource").value;
  $("fxSource").value = $("fxTarget").value;
  $("fxTarget").value = source;
};

$("btnFxConvert").onclick = async () => {
  const body = {
    amount: $("fxAmount").value,
    sourceCurrency: $("fxSource").value,
    targetCurrency: $("fxTarget").value,
  };
  try {
    const result = await api("/api/fx/convert", { method: "POST", body: JSON.stringify(body) });
    $("fxResult").classList.remove("muted");
    $("fxResult").innerHTML = `<strong>${escapeHtml(formatMoney(result.amount, result.sourceCurrency))}</strong>
      <span>→</span><strong>${escapeHtml(formatMoney(result.convertedAmount, result.targetCurrency))}</strong>
      <span class="muted">Rate: ${escapeHtml(result.rate)}</span>`;
    show($("outFx"), result);
  } catch (e) {
    show($("outFx"), { error: e.message, body: e.body });
  }
};

$("btnMarketPrice").onclick = () => loadMarketQuote(false);
$("btnMarketRefresh").onclick = () => loadMarketQuote(true);
$("btnMarketDetail").onclick = () => {
  const { assetType, symbol } = selectedMarketAsset();
  if (!assetType || !symbol) return;
  openAssetDetail({ type: assetType, slug: symbol });
};

$("marketPopular").onchange = () => {
  $("marketResults").value = "";
};

$("marketResults").onchange = () => {
  if ($("marketResults").value) loadMarketQuote(false);
};

function renderMarketResults(results) {
  const items = Array.isArray(results) ? results : [];
  $("marketResults").innerHTML = `<option value="">${items.length ? `Select a result (${items.length})` : "No results"}</option>${items
    .map(
      (item) =>
        `<option value="${escapeHtml(`${item.assetType}|${item.symbol}|${item.assetId || ""}`)}">${escapeHtml(
          `${item.name} (${item.symbol})`
        )}</option>`
    )
    .join("")}`;
}

$("btnMarketSearch").onclick = async () => {
  const query = $("marketQuery").value.trim();
  const type = $("marketType").value;
  if (!query) {
    show($("outMarket"), { error: "Enter a symbol or asset name, or use List all" });
    return;
  }
  try {
    let results = await api(`/api/assets/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`);
    if ((!results || !results.length) && type === "crypto" && /^[A-Za-z]{2,4}$/.test(query)) {
      results = await api(`/api/assets/search?q=${encodeURIComponent(query)}&type=stock`);
      if (results && results.length) $("marketType").value = "stock";
    }
    renderMarketResults(results);
    show($("outMarket"), results);
  } catch (e) {
    show($("outMarket"), { error: e.message, body: e.body });
  }
};

$("btnMarketList").onclick = async () => {
  const type = $("marketType").value;
  try {
    const results = await api(`/api/assets?type=${encodeURIComponent(type)}&limit=2000`);
    renderMarketResults(results);
    show($("outMarket"), { listed: results.length, type, sample: results.slice(0, 8) });
  } catch (e) {
    show($("outMarket"), { error: e.message, body: e.body });
  }
};

$("btnNews").onclick = async () => {
  try {
    const items = await api("/api/news?limit=50");
    renderNews(items);
    show($("outNews"), items);
  } catch (e) {
    show($("outNews"), { error: e.message, body: e.body });
  }
};

$("btnHistory").onclick = async () => {
  try {
    const id = $("histId").value.trim();
    const type = $("histType").value;
    const range = $("histRange").value;
    const data = await api(
      `/api/assets/${encodeURIComponent(id)}/history?range=${encodeURIComponent(range)}&type=${encodeURIComponent(type)}`
    );
    show($("outHistory"), data);
  } catch (e) {
    show($("outHistory"), { error: e.message, body: e.body });
  }
};

$("btnSnapList").onclick = async () => {
  const params = new URLSearchParams();
  if ($("snapFrom").value) params.set("from", $("snapFrom").value);
  if ($("snapTo").value) params.set("to", $("snapTo").value);
  const q = params.toString() ? `?${params}` : "";
  try {
    const rows = await api(`/api/snapshots${q}`);
    $("snapTable").innerHTML = Array.isArray(rows) && rows.length
      ? `<table><thead><tr><th>Date</th><th>Created</th></tr></thead><tbody>${rows
          .map(
            (r) =>
              `<tr><td><button type="button" class="clickable snap-date" data-date="${escapeHtml(
                r.date
              )}">${escapeHtml(r.date)}</button></td><td>${escapeHtml(r.createdAt || "")}</td></tr>`
          )
          .join("")}</tbody></table>`
      : "<p class='muted'>No snapshots</p>";
    show($("outSnap"), rows);
  } catch (e) {
    show($("outSnap"), { error: e.message, body: e.body });
  }
};

$("btnSnapGet").onclick = async () => {
  const date = $("snapDate").value;
  if (!date) {
    show($("outSnap"), { error: "Pick a date" });
    return;
  }
  try {
    show($("outSnap"), await api(`/api/snapshots/${encodeURIComponent(date)}`));
  } catch (e) {
    show($("outSnap"), { error: e.message, body: e.body });
  }
};

$("snapTable").addEventListener("click", (e) => {
  const btn = e.target.closest(".snap-date");
  if (!btn) return;
  $("snapDate").value = btn.dataset.date;
  $("btnSnapGet").click();
});

$("btnAdminSettings").onclick = async () => {
  try {
    show($("outAdmin"), await api("/api/admin/settings"));
  } catch (e) {
    show($("outAdmin"), { error: e.message, body: e.body });
  }
};

$("btnAdminRss").onclick = async () => {
  try {
    show($("outAdmin"), await api("/api/admin/rss-sources"));
  } catch (e) {
    show($("outAdmin"), { error: e.message, body: e.body });
  }
};

$("btnAdminJobs").onclick = async () => {
  try {
    show($("outAdmin"), await api("/api/admin/job-runs"));
  } catch (e) {
    show($("outAdmin"), { error: e.message, body: e.body });
  }
};

$("btnS3Refresh").onclick = async () => {
  const prefix = $("s3Prefix").value;
  const params = new URLSearchParams({ limit: "200" });
  if (prefix) params.set("prefix", prefix);
  try {
    const data = await api(`/api/dev/s3?${params}`);
    const keys = data.keys || [];
    const selected = $("s3Key").value;
    $("s3Key").innerHTML = `<option value="">${keys.length ? `Select a key (${keys.length})` : "No keys"}</option>${keys
      .map((key) => `<option value="${escapeHtml(key)}">${escapeHtml(key)}</option>`)
      .join("")}`;
    if (keys.includes(selected)) $("s3Key").value = selected;
    $("s3Summary").innerHTML = `<p class="muted">backend: ${escapeHtml(
      data.backend || ""
    )} · bucket: ${escapeHtml(data.bucket || "—")} · endpoint: ${escapeHtml(data.endpoint || "—")}</p>`;
    show($("outS3"), data);
  } catch (e) {
    show($("outS3"), { error: e.message, body: e.body });
  }
};

$("btnS3Get").onclick = async () => {
  const key = $("s3Key").value;
  if (!key) {
    show($("outS3"), { error: "Select a key first (load an Asset so profile/ is written)" });
    return;
  }
  try {
    show($("outS3"), await api(`/api/dev/s3/object?key=${encodeURIComponent(key)}`));
  } catch (e) {
    show($("outS3"), { error: e.message, body: e.body });
  }
};

$("s3Key").onchange = () => {
  if ($("s3Key").value) $("btnS3Get").click();
};

$("btnDynamoRefresh").onclick = async () => {
  try {
    const data = await api("/api/dev/dynamodb");
    renderDynamoTables(data);
    show($("outDynamo"), data);
  } catch (e) {
    show($("outDynamo"), { error: e.message, body: e.body });
  }
};

$("btnDynamoScan").onclick = async () => {
  const table = $("dynamoTable").value;
  if (!table) {
    show($("outDynamo"), { error: "Select a table first" });
    return;
  }
  const limit = Math.min(100, Math.max(1, Number($("dynamoLimit").value) || 25));
  try {
    show(
      $("outDynamo"),
      await api(`/api/dev/dynamodb/${encodeURIComponent(table)}?limit=${limit}`)
    );
  } catch (e) {
    show($("outDynamo"), { error: e.message, body: e.body });
  }
};

// ---- Chat ----

const chatHistory = [];
let chatModelsLoaded = false;

function renderChatLog() {
  const host = $("chatLog");
  if (!chatHistory.length) {
    host.innerHTML = "<p class='muted'>No messages yet.</p>";
    return;
  }
  host.innerHTML = chatHistory
    .map((msg) => {
      if (msg.role === "pending") {
        return `<div class="chat-bubble pending">Thinking…</div>`;
      }
      const tools = (msg.toolCalls || [])
        .map((tc) => {
          const ok = tc.ok !== false;
          return `<span class="chat-tool ${ok ? "ok" : "err"}">${escapeHtml(tc.name || "tool")}${
            ok ? "" : " failed"
          }</span>`;
        })
        .join("");
      const meta = msg.model
        ? `<div class="muted" style="margin-top:0.35rem;font-size:0.72rem">${escapeHtml(msg.model)}</div>`
        : "";
      return `<div class="chat-bubble ${escapeHtml(msg.role)}">${escapeHtml(
        msg.content || ""
      )}${tools ? `<div class="chat-tools">${tools}</div>` : ""}${meta}</div>`;
    })
    .join("");
  host.scrollTop = host.scrollHeight;
}

async function loadChatModels() {
  const select = $("chatModel");
  const previous = select.value;
  try {
    const free = $("chatFreeOnly").checked;
    const data = await api(`/api/chat/models?free=${free ? "true" : "false"}&tools=true`);
    const models = data.models || [];
    const opts = [`<option value="">default (${escapeHtml(data.defaultModel || "provider")})</option>`];
    for (const m of models) {
      const label = `${m.id}${m.free ? " · free" : ""}${m.tools ? "" : " · no-tools"}`;
      opts.push(`<option value="${escapeHtml(m.id)}">${escapeHtml(label)}</option>`);
    }
    select.innerHTML = opts.join("");
    if (previous && models.some((m) => m.id === previous)) select.value = previous;
    chatModelsLoaded = true;
    const status = data.configured
      ? `${models.length} models · ${data.provider}`
      : "LLM not configured (set OPENROUTER_API_KEY)";
    show($("outChat"), { ...data, status });
  } catch (e) {
    show($("outChat"), { error: e.message, body: e.body });
  }
}

async function sendChat() {
  const input = $("chatInput");
  const text = (input.value || "").trim();
  if (!text) return;
  if (!getToken()) {
    show($("outChat"), { error: "Set a Bearer token first (e.g. fake:alice)" });
    return;
  }
  input.value = "";
  chatHistory.push({ role: "user", content: text });
  chatHistory.push({ role: "pending", content: "" });
  renderChatLog();
  $("btnChatSend").disabled = true;
  const historyPayload = chatHistory
    .filter((m) => m.role === "user" || m.role === "assistant")
    .slice(-16)
    .map((m) => ({ role: m.role, content: m.content }));
  // last user is also `message`; don't duplicate it in history
  if (historyPayload.length && historyPayload[historyPayload.length - 1].role === "user") {
    historyPayload.pop();
  }
  const body = {
    message: text,
    history: historyPayload,
    freeOnly: $("chatFreeOnly").checked,
  };
  const model = $("chatModel").value.trim();
  if (model) body.model = model;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 240000);
  try {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${getApiBase()}/api/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const raw = await res.text();
    let data;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = raw;
    }
    chatHistory.pop();
    if (!res.ok) {
      chatHistory.push({
        role: "assistant",
        content: `Error HTTP ${res.status}: ${typeof data === "string" ? data : JSON.stringify(data)}`,
      });
      show($("outChat"), { error: `HTTP ${res.status}`, body: data });
    } else {
      chatHistory.push({
        role: "assistant",
        content: data.reply || "",
        toolCalls: data.toolCalls || [],
        model: data.model,
      });
      show($("outChat"), data);
    }
    renderChatLog();
  } catch (e) {
    chatHistory.pop();
    chatHistory.push({
      role: "assistant",
      content: e.name === "AbortError" ? "Request timed out." : e.message,
    });
    renderChatLog();
    show($("outChat"), { error: e.message, body: e.body });
  } finally {
    clearTimeout(timer);
    $("btnChatSend").disabled = false;
  }
}

$("btnChatModels").onclick = () => loadChatModels();
$("chatFreeOnly").onchange = () => loadChatModels();
$("btnChatClear").onclick = () => {
  chatHistory.length = 0;
  renderChatLog();
  show($("outChat"), { cleared: true });
};
$("btnChatSend").onclick = () => sendChat();
$("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
});
renderChatLog();

loadAuth();

window.addEventListener("hashchange", () => {
  const q = parseAssetHash();
  if (q) openAssetDetail(q);
});

const initialAsset = parseAssetHash();
if (initialAsset) {
  openAssetDetail(initialAsset);
}
