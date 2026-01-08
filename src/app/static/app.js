let chartInstance = null;

function fmt(n) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 6 }).format(n);
}

async function convert() {
  const amount = document.getElementById("amount").value;
  const from = document.getElementById("from").value;
  const to = document.getElementById("to").value;

  const resultEl = document.getElementById("result");
  const rateInfoEl = document.getElementById("rateInfo");

  resultEl.textContent = "…";
  rateInfoEl.textContent = "…";

  const url = `/api/convert?amount=${encodeURIComponent(amount)}&from_ccy=${encodeURIComponent(from)}&to_ccy=${encodeURIComponent(to)}`;
  const res = await fetch(url);
  const data = await res.json();

  if (!res.ok) {
    resultEl.textContent = "Error";
    rateInfoEl.textContent = data?.detail || "Unknown error";
    return;
  }

  resultEl.textContent = `${fmt(data.converted)} ${data.to}`;
  rateInfoEl.textContent = `FX: 1 ${data.from} = ${data.fx_rate} ${data.to} · Date: ${data.date || "—"}`;
}

function openModal() {
  const modal = document.getElementById("modal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

function closeModal() {
  const modal = document.getElementById("modal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

async function showTrend(symbol) {
  const title = document.getElementById("modalTitle");
  const metaEl = document.getElementById("modalMeta");
  title.textContent = `Trend 30d · USD → ${symbol}`;
  metaEl.textContent = "Loading…";

  openModal();

  const res = await fetch(`/api/timeseries?symbol=${encodeURIComponent(symbol)}&days=30`);
  const data = await res.json();

  if (!res.ok) {
    metaEl.textContent = data?.detail || "Unable to load timeseries";
    return;
  }

  const labels = (data.points || []).map(p => p.date);
  const values = (data.points || []).map(p => p.value);

  const ctx = document.getElementById("chart");

  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: `USD → ${symbol}`,
        data: values,
        tension: 0.25,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: true },
        tooltip: { enabled: true }
      },
      scales: {
        x: { ticks: { maxTicksLimit: 8 } },
        y: { beginAtZero: false }
      }
    }
  });

  const meta = data.meta || {};
  metaEl.textContent = `Points: ${values.length} · Cached: ${meta.cached ? "yes" : "no"}${meta.stale ? " (stale)" : ""}`;
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btnConvert").addEventListener("click", convert);
  document.getElementById("btnClose").addEventListener("click", closeModal);

  // Convert al entrar
  convert().catch(() => {});

  // Trend buttons
  document.querySelectorAll(".btnTrend").forEach(btn => {
    btn.addEventListener("click", () => showTrend(btn.dataset.symbol));
  });

  // Close modal al click afuera
  document.getElementById("modal").addEventListener("click", (e) => {
    if (e.target.id === "modal") closeModal();
  });
});
