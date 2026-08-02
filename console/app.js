const liveReportUrl = "data/public-report.json";

const demoReport = {
  schema: "bountyguard.report.v1",
  status: "payout_detected",
  checked_at: "2026-08-02T23:10:00Z",
  address_display: "7y9K2b…WNCsS",
  message: "Simulated replay: one verified finalized payout event detected.",
  balances: { SOL: "0", USDC: "500", USDG: "0" },
  events: [{
    signature: "demo_signature_not_on_chain",
    slot: 352000000,
    block_time: 1785712200,
    payouts: [{ asset: "USDC", amount: "500", mint: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" }],
    unverified_assets: []
  }],
  receipt: "sha256:4fd8a35d22c93e6f8470fbe90b68e6a1f66c1f5b78935748d24af16ad4d0f7d2"
};

let liveReport;
let demoMode = false;

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[character]);

function statusMeta(status) {
  if (status === "payout_detected") return ["Payout detected", "Verified", "good"];
  if (status === "attention") return ["Review required", "Attention", "attention"];
  if (status === "verification_failed") return ["Verification failed", "Failed", "failed"];
  if (status === "baseline_created") return ["Baseline secured", "Guarding", "good"];
  return ["No new payout", "Guarding", "good"];
}

function assetMark(asset) {
  return asset === "SOL" ? "S" : asset === "USDC" ? "$" : "G";
}

function renderBalances(balances = {}) {
  const order = ["SOL", "USDC", "USDG"];
  $("#balances").innerHTML = order.map(asset => {
    const amount = balances[asset] ?? "0";
    const subtitle = asset === "SOL" ? "Native asset" : "Verified mint";
    return `<div class="balance-line"><span class="asset-mark">${assetMark(asset)}</span><div><strong>${asset}</strong><small>${subtitle}</small></div><strong>${escapeHtml(amount)}</strong></div>`;
  }).join("");
}

function renderActivity(events = [], isDemo) {
  const payouts = events.flatMap(event => (event.payouts || []).map(payout => ({ event, payout })));
  $("#event-count").textContent = `${payouts.length} ${payouts.length === 1 ? "event" : "events"}`;
  if (!payouts.length) {
    $("#activity").innerHTML = `<div class="empty-activity"><div><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.7 2.8 7.9 7 9.5 4.2-1.6 7-4.8 7-9.5V6l-7-3Zm-3 9 2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg><strong>No new finalized payout</strong><p>The baseline is active. New incoming SOL or allowlisted stablecoins will appear here with their transaction evidence.</p></div></div>`;
    return;
  }
  $("#activity").innerHTML = payouts.map(({ event, payout }) => {
    const explorer = isDemo ? "" : `https://solscan.io/tx/${encodeURIComponent(event.signature)}`;
    return `<div class="event"><span class="event-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span><div><strong>Incoming ${escapeHtml(payout.asset)} verified</strong><small>${isDemo ? "SIMULATION — no on-chain claim" : `Finalized slot ${escapeHtml(event.slot || "—")}`}</small></div><div class="event-amount"><strong>+${escapeHtml(payout.amount)} ${escapeHtml(payout.asset)}</strong>${explorer ? `<a href="${explorer}" target="_blank" rel="noreferrer">View transaction</a>` : ""}</div></div>`;
  }).join("");
}

function render(report, isDemo = false) {
  const [title, badge, className] = statusMeta(report.status);
  $("#status-title").textContent = title;
  $("#status-badge").textContent = badge;
  $("#status-badge").className = `status-badge ${className}`;
  $("#status-message").textContent = report.message || "Evidence report loaded.";
  $("#address").textContent = report.address_display || "unavailable";
  $("#checked-at").textContent = new Date(report.checked_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";
  $("#receipt").textContent = report.receipt || "sha256:unavailable";
  renderBalances(report.balances);
  renderActivity(report.events, isDemo);

  $("#mode-banner").className = `mode-banner ${isDemo ? "simulation" : "live"}`;
  $("#mode-label").textContent = isDemo ? "SIMULATED REPLAY" : "LIVE EVIDENCE";
  $("#mode-description").textContent = isDemo ? "Illustrative $500 event — not an earnings claim" : "Latest locally verified report";
  $("#mode-toggle").setAttribute("aria-pressed", String(isDemo));
  $("#mode-toggle").lastChild.textContent = isDemo ? " Return to live evidence" : " Replay a $500 payout";
}

async function load() {
  try {
    const response = await fetch(liveReportUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    liveReport = await response.json();
  } catch (error) {
    liveReport = {
      schema: "bountyguard.report.v1",
      status: "verification_failed",
      checked_at: new Date().toISOString(),
      address_display: "unavailable",
      message: "The public evidence snapshot could not be loaded.",
      balances: { SOL: "—", USDC: "—", USDG: "—" },
      events: [],
      receipt: "sha256:unavailable"
    };
  }
  render(liveReport, false);
}

$("#mode-toggle").addEventListener("click", () => {
  demoMode = !demoMode;
  render(demoMode ? demoReport : liveReport, demoMode);
});

$("#copy-receipt").addEventListener("click", async () => {
  const button = $("#copy-receipt");
  try {
    await navigator.clipboard.writeText($("#receipt").textContent);
    button.setAttribute("aria-label", "Receipt copied");
    setTimeout(() => button.setAttribute("aria-label", "Copy report receipt"), 1800);
  } catch (_) {
    button.setAttribute("aria-label", "Copy unavailable");
  }
});

load();
