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
  const lines = data?.lines || [];
  if (!lines.length) {
    host.innerHTML = "<p class='muted'>No lines</p>";
    return;
  }
  const rows = lines
    .map(
      (l) => `<tr>
      <td>${l.assetType || ""}</td>
      <td>${l.symbol || ""}</td>
      <td>${l.qty ?? ""}</td>
      <td>${l.price ?? "—"}</td>
      <td>${l.marketValue ?? "—"}</td>
      <td>${l.pnl ?? "—"}</td>
      <td>${l.currency || ""}</td>
      <td>${l.missingPrice ? "yes" : ""}</td>
    </tr>`
    )
    .join("");
  host.innerHTML = `<table>
    <thead><tr>
      <th>Type</th><th>Symbol</th><th>Qty</th><th>Price</th>
      <th>MV</th><th>PnL</th><th>CCY</th><th>Missing</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>
  <p class="muted">totalsDisplay: ${JSON.stringify(data.totalsDisplay)} · fx: ${data.fx?.status}</p>`;
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
  if (btn) switchTab(btn.dataset.tab);
});

$("btnHealth").onclick = async () => {
  try {
    show($("outHealth"), await api("/health"));
  } catch (e) {
    show($("outHealth"), { error: e.message, body: e.body });
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
    show($("outWatch"), await api("/api/watchlist"));
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

$("marketPopular").onchange = () => {
  $("marketResults").value = "";
};

$("marketResults").onchange = () => {
  if ($("marketResults").value) loadMarketQuote(false);
};

$("btnMarketSearch").onclick = async () => {
  const query = $("marketQuery").value.trim();
  const type = $("marketType").value;
  if (!query) {
    show($("outMarket"), { error: "Enter a symbol or asset name" });
    return;
  }
  try {
    const results = await api(`/api/assets/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`);
    $("marketResults").innerHTML = `<option value="">${results.length ? "Select a result" : "No results"}</option>${results
      .map((item) => `<option value="${escapeHtml(`${item.assetType}|${item.symbol}|${item.assetId || ""}`)}">${escapeHtml(`${item.name} (${item.symbol})`)}</option>`)
      .join("")}`;
    show($("outMarket"), results);
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

loadAuth();
