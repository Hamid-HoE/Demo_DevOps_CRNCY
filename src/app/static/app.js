(() => {
  const $ = (id) => document.getElementById(id);

  const amountEl = $("amount");
  const fromEl = $("from");
  const toEl = $("to");
  const btnEl = $("btnConvert");

  const resultBox = $("resultBox");
  const resultValue = $("resultValue");
  const resultHint = $("resultHint");

  let cachedRates = null;
  let cachedAt = 0;
  const CACHE_MS = 30_000;

  function setBox(state /* "ok" | "err" | "" */) {
    if (!resultBox) return;
    resultBox.classList.remove("ok", "err");
    if (state) resultBox.classList.add(state);
  }

  function setResult(valueText, hintText = "", state = "") {
    if (resultValue) resultValue.textContent = valueText;
    if (resultHint) resultHint.textContent = hintText;
    setBox(state);
  }

  function toNumber(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : NaN;
  }

  function formatNumber(n) {
    // 2 a 6 decimales dependiendo magnitud
    const abs = Math.abs(n);
    const decimals = abs >= 100 ? 2 : abs >= 1 ? 4 : 6;
    return n.toFixed(decimals);
  }

  async function fetchRates() {
    const now = Date.now();
    if (cachedRates && (now - cachedAt) < CACHE_MS) return cachedRates;

    const res = await fetch("/api/rates", { headers: { "accept": "application/json" } });
    if (!res.ok) throw new Error(`GET /api/rates failed (${res.status})`);
    const data = await res.json();

    cachedRates = data;
    cachedAt = now;
    return data;
  }

  async function convert() {
    try {
      btnEl && (btnEl.disabled = true);
      setResult("…", "Calculando...");

      const amount = toNumber(amountEl?.value);
      const from = (fromEl?.value || "").trim().toUpperCase();
      const to = (toEl?.value || "").trim().toUpperCase();

      if (!Number.isFinite(amount) || amount <= 0) {
        setResult("—", "Ingresa un monto válido (> 0).", "err");
        return;
      }
      if (!from || !to) {
        setResult("—", "Selecciona monedas From/To.", "err");
        return;
      }
      if (from === to) {
        setResult(`${formatNumber(amount)} ${to}`, "", "ok");
        return;
      }

      const data = await fetchRates();
      const base = (data.base || "USD").toUpperCase();
      const rates = data.rates || {};

      const rateFrom = (from === base) ? 1.0 : rates[from];
      const rateTo = (to === base) ? 1.0 : rates[to];

      if (rateFrom == null) {
        setResult("—", `No hay tasa para ${from}. (Moneda no soportada por la API)`, "err");
        return;
      }
      if (rateTo == null) {
        setResult("—", `No hay tasa para ${to}. (Moneda no soportada por la API)`, "err");
        return;
      }

      // Cross-rate usando base (USD):
      // amount_from -> amount_base -> amount_to
      const amountInBase = amount / Number(rateFrom);
      const out = amountInBase * Number(rateTo);

      setResult(`${formatNumber(out)} ${to}`, `${formatNumber(amount)} ${from} → ${to} (base ${base})`, "ok");
    } catch (e) {
      const msg = (e && e.message) ? e.message : String(e);
      setResult("Error", msg, "err");
      console.error(e);
    } finally {
      btnEl && (btnEl.disabled = false);
    }
  }

  function bind() {
    if (!btnEl) return;

    btnEl.addEventListener("click", (ev) => {
      ev.preventDefault();
      convert();
    });

    amountEl?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        convert();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bind();
  });
})();
