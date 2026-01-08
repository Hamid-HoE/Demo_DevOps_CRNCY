async function jget(url) {
  const r = await fetch(url, { headers: { "Accept": "application/json" } });
  const txt = await r.text();
  let data = null;
  try { data = JSON.parse(txt); } catch { /* ignore */ }
  if (!r.ok) {
    const msg = (data && (data.error || data.message)) ? (data.error || data.message) : txt;
    throw new Error(msg || `HTTP ${r.status}`);
  }
  return data;
}

function setResult(kind, main, hint = "") {
  const box = document.getElementById("resultBox");
  const v = document.getElementById("resultValue");
  const h = document.getElementById("resultHint");
  box.classList.remove("ok", "err");
  box.classList.add(kind);
  v.textContent = main;
  h.textContent = hint;
}

async function doConvert() {
  const amount = Number(document.getElementById("amount").value || "0");
  const from = document.getElementById("from").value;
  const to = document.getElementById("to").value;

  if (!amount || amount <= 0) {
    setResult("err", "Invalid amount", "Enter a value > 0");
    return;
  }

  setResult("", "Converting…", "");

  try {
    const data = await jget(`/api/convert?amount=${encodeURIComponent(amount)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    setResult(
      "ok",
      `${data.result} ${data.to}`,
      `${data.amount} ${data.from} → ${data.to} (fx date: ${data.fx_date || "—"})`
    );
  } catch (e) {
    setResult("err", "Error", String(e.message || e));
  }
}

function openModal() {
  const m = document.getElementById("modal");
  m.classList.remove("hidden");
  m.setAttribute("aria-hidden", "false");
}
function closeModal() {
  const m = document.getElementById("modal");
  m.classList.add("hidden");
  m.setAttribute("aria-hidden", "true");
}

function drawTrend(points, title) {
  const canvas = document.getElementById("trendCanvas");
  const ctx = canvas.getContext("2d");

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!points || points.length < 2) {
    ctx.fillText("No data available.", 20, 40);
    return;
  }

  const pad = 40;
  const w = canvas.width - pad * 2;
  const h = canvas.height - pad * 2;

  const ys = points.map(p => p.rate);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const span = (maxY - minY) || 1;

  // Axes
  ctx.globalAlpha = 0.35;
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, pad + h);
  ctx.lineTo(pad + w, pad + h);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Title
  ctx.fillText(title, pad, 18);

  // Line (default stroke)
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad + (i * w) / (points.length - 1);
    const y = pad + h - ((p.rate - minY) / span) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Labels
  const last = points[points.length - 1];
  ctx.fillText(`min: ${minY.toFixed(4)}  max: ${maxY.toFixed(4)}  last: ${last.rate.toFixed(4)}`, pad, canvas.height - 12);
}

async function showTrend(symbol) {
  try {
    const data = await jget(`/api/trend?symbol=${encodeURIComponent(symbol)}&days=30`);
    const points = data.points || [];
    document.getElementById("modalTitle").textContent = `Trend · USD → ${symbol}`;
    document.getElementById("modalMeta").textContent = `Points: ${points.length} (working days)`;
    openModal();
    drawTrend(points, `USD → ${symbol} (last 30 days)`);
  } catch (e) {
    alert(`Trend error: ${String(e.message || e)}`);
  }
}

function wire() {
  document.getElementById("btnConvert")?.addEventListener("click", doConvert);

  // Trend links
  document.querySelectorAll("a.trend").forEach(a => {
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      const sym = a.getAttribute("data-symbol");
      if (sym) showTrend(sym);
    });
  });

  document.getElementById("modalClose")?.addEventListener("click", closeModal);
  document.getElementById("modalX")?.addEventListener("click", closeModal);
}

document.addEventListener("DOMContentLoaded", wire);
