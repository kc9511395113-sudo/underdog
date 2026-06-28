function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function showToast(msg) {
  const el = document.querySelector("#toast");
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 4000);
}

function renderShortlist(shortlist, linkField = "finviz_url") {
  const container = document.querySelector("#shortlist");
  if (!container) return;
  container.innerHTML = "";
  for (const key of ["1", "2", "3"]) {
    const tier = shortlist[key];
    if (!tier) continue;
    const card = document.createElement("div");
    card.className = "tier-card";
    card.dataset.tier = key;
    card.innerHTML = `
      <div class="tier-header">
        <span class="tier-badge">${tier.label}</span>
        <span class="tier-title">${tier.title}</span>
        <p class="tier-desc">${tier.description}</p>
      </div>
      <div class="stock-list"></div>
    `;
    const list = card.querySelector(".stock-list");
    if (!tier.stocks.length) {
      list.innerHTML = `<p style="padding:1rem;color:var(--muted);font-size:0.85rem">No stocks in this tier this week.</p>`;
    } else {
      tier.stocks.forEach((s) => {
        const url = s[linkField] || s.stats_url || s.quote_url || "#";
        const row = document.createElement("div");
        row.className = "stock-row";
        row.innerHTML = `
          <a class="stock-ticker" href="${url}" target="_blank" rel="noopener">${s.ticker}</a>
          <div>
            <div class="stock-name">${s.company || s.ticker}</div>
            ${s.note ? `<div class="stock-note">${s.note}</div>` : ""}
          </div>
          <div class="stock-metrics">
            <span class="metric good">FWD ${s.fpe_n}×</span>
            <span class="metric">P/B ${s.pb_n}</span>
            <span class="metric">${s.div_n}%</span>
            <span class="metric ${(s.week_flow_n ?? 0) >= 0 ? "good" : "warn"}">${s.week_flow || "—"}</span>
            <span class="metric">${s.mcap}</span>
          </div>
        `;
        list.appendChild(row);
      });
    }
    container.appendChild(card);
  }
}

function renderResults(results, linkField = "finviz_url") {
  const tbody = document.querySelector("#results-table tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  results.forEach((r, i) => {
    const url = r[linkField] || r.stats_url || r.quote_url || "#";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><a href="${url}" target="_blank" rel="noopener">${r.ticker}</a></td>
      <td>${r.company || "—"}</td>
      <td>${r.type || "—"}</td>
      <td><span class="tier-pill t${r.tier}">T${r.tier}</span></td>
      <td>${r.fpe_n}</td>
      <td>${r.pb_n}</td>
      <td>${r.div_n}%</td>
      <td class="${(r.week_flow_n ?? 0) >= 0 ? "flow-pos" : "flow-neg"}">${r.week_flow || "—"}</td>
      <td>${r.mcap}</td>
      <td>${(r.industry || "").slice(0, 32)}</td>
    `;
    tbody.appendChild(tr);
  });
  const countEl = document.querySelector("#results-count");
  if (countEl) countEl.textContent = `${results.length} stocks pass all three criteria`;
}

function renderNearMisses(near, linkField = "finviz_url") {
  const section = document.querySelector("#near-misses-section");
  const tbody = document.querySelector("#near-table tbody");
  if (!section || !tbody) return;
  if (!near || !near.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  tbody.innerHTML = "";
  near.forEach((r) => {
    const url = r[linkField] || r.stats_url || r.quote_url || "#";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><a href="${url}" target="_blank" rel="noopener">${r.ticker}</a></td>
      <td>${r.company || "—"}</td>
      <td>${r.fpe_n}</td>
      <td>${r.pb_n}</td>
      <td>${r.div_n}%</td>
      <td class="${(r.week_flow_n ?? 0) >= 0 ? "flow-pos" : "flow-neg"}">${r.week_flow || "—"}</td>
      <td>${r.mcap}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderData(data, cfg) {
  const sc = data.screener || {};
  const meta = data.meta || {};
  const counts = data.counts || {};

  const lastEl = document.querySelector("#last-updated");
  const nextEl = document.querySelector("#next-refresh");
  if (lastEl) lastEl.textContent = `Updated: ${fmtDate(meta.last_updated)}`;
  if (nextEl) nextEl.textContent = `Next: ${fmtDate(meta.next_refresh)}`;

  const benchEl = document.querySelector("#benchmark-pe");
  if (benchEl) {
    benchEl.textContent = sc.sp500_forward_pe
      ? `${sc.sp500_forward_pe}×`
      : sc.hang_seng_forward_pe
        ? `${sc.hang_seng_forward_pe}×`
        : "—";
  }

  const benchLabel = document.querySelector("#benchmark-label");
  if (benchLabel && sc.hang_seng_forward_pe) {
    benchLabel.textContent = "Hang Seng Fwd P/E";
  }

  const universeEl = document.querySelector("#stat-universe");
  if (universeEl) universeEl.textContent = counts.universe ?? counts.scanned ?? "—";

  const passingEl = document.querySelector("#stat-passing");
  if (passingEl) passingEl.textContent = counts.passing ?? data.results?.length ?? "—";

  const nearEl = document.querySelector("#stat-near");
  if (nearEl) nearEl.textContent = counts.near_misses ?? data.near_misses?.length ?? "—";

  const linkEl = document.querySelector("#source-link");
  if (linkEl) {
    linkEl.href = sc.finviz_url || sc.list_url || "#";
    if (cfg.sourceLinkText) linkEl.textContent = cfg.sourceLinkText;
  }

  renderShortlist(data.shortlist || {}, cfg.linkField);
  renderResults(data.results || [], cfg.linkField);
  renderNearMisses(data.near_misses || [], cfg.linkField);
}

function initScreener(cfg) {
  const $ = (sel) => document.querySelector(sel);

  async function loadData() {
    const res = await fetch(cfg.apiData);
    const data = await res.json();
    renderData(data, cfg);
  }

  async function pollRefresh() {
    const res = await fetch(cfg.apiStatus);
    const status = await res.json();
    const btn = $("#btn-refresh");
    if (status.refreshing) {
      if (btn) { btn.disabled = true; btn.textContent = "↻ Loading…"; }
      setTimeout(pollRefresh, 3000);
    } else {
      if (btn) { btn.disabled = false; btn.textContent = "↻ Refresh"; }
      await loadData();
    }
  }

  const btn = $("#btn-refresh");
  if (btn) {
    btn.addEventListener("click", async () => {
      const res = await fetch(cfg.apiRefresh, { method: "POST" });
      if (res.status === 409) {
        showToast("Refresh already in progress…");
        pollRefresh();
        return;
      }
      showToast(cfg.refreshToast || "Refresh started…");
      pollRefresh();
    });
  }

  loadData();
}