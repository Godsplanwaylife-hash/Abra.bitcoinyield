(function () {
  const root = document.getElementById("contract-root");
  if (!root) return;

  const symbol = root.dataset.symbol;
  const tvSymbol = root.dataset.tv;
  const payoutRate = parseFloat(root.dataset.payout);
  const minStake = parseFloat(root.dataset.min);
  let balance = parseFloat(root.dataset.balance);
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  const INTERVALS = { "1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "1d": "D" };
  const fmt = (n) => n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  /* ---- TradingView chart + timeframe buttons ---- */
  function renderChart(tf) {
    if (typeof TradingView === "undefined") {
      document.getElementById("tv_chart").innerHTML =
        '<p class="muted center" style="padding:24px">Chart could not be loaded. Check your connection.</p>';
      return;
    }
    document.getElementById("tv_chart").innerHTML = "";
    new TradingView.widget({
      autosize: true, symbol: tvSymbol, interval: INTERVALS[tf], timezone: "Etc/UTC",
      theme: "dark", style: "1", locale: "en", enable_publishing: false,
      hide_top_toolbar: true, hide_side_toolbar: true, allow_symbol_change: false,
      backgroundColor: "#171e2e", container_id: "tv_chart",
    });
  }
  document.querySelectorAll(".tf").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tf").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderChart(btn.dataset.tf);
    });
  });
  renderChart("15m");

  /* ---- Order panel ---- */
  let duration = parseInt(document.querySelector("#duration-seg .active").dataset.duration, 10);
  document.querySelectorAll("#duration-seg .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#duration-seg .seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      duration = parseInt(btn.dataset.duration, 10);
    });
  });

  const amountInput = document.getElementById("amount");
  document.querySelectorAll(".quick .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      amountInput.value = Math.floor(balance * parseFloat(btn.dataset.pct) * 100) / 100;
    });
  });

  const msg = document.getElementById("trade-msg");
  function say(text, ok) { msg.textContent = text; msg.className = "trade-msg " + (ok ? "ok" : "error"); }

  document.querySelectorAll(".btn-buy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const amount = parseFloat(amountInput.value);
      if (!(amount >= minStake)) return say("Minimum stake is " + minStake + " USDT.", false);
      if (amount > balance) return say("Not enough demo balance.", false);

      document.querySelectorAll(".btn-buy").forEach((b) => (b.disabled = true));
      try {
        const res = await fetch("/contract/trade", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({ symbol, direction: btn.dataset.dir, amount, duration }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Trade failed.");
        say("Contract opened at $" + fmt(data.entry_price) + ".", true);
        setTimeout(() => location.reload(), 700);
      } catch (err) {
        say(err.message, false);
        document.querySelectorAll(".btn-buy").forEach((b) => (b.disabled = false));
      }
    });
  });

  /* ---- Live price refresh (server caches ~60s) ---- */
  async function refreshPrice() {
    try {
      const res = await fetch("/contract/api/price?symbol=" + symbol);
      const data = await res.json();
      if (data.price) document.getElementById("live-price").textContent = "$" + fmt(data.price);
    } catch (_) { /* keep last price */ }
  }
  setInterval(refreshPrice, 30000);

  /* ---- Countdowns + settlement ---- */
  const timers = document.querySelectorAll(".countdown");
  let settling = false;
  async function settle() {
    if (settling) return;
    settling = true;
    try {
      await fetch("/contract/settle", { method: "POST", headers: { "X-CSRFToken": csrf } });
    } finally { location.reload(); }
  }
  function tick() {
    const now = Date.now();
    timers.forEach((el) => {
      const left = Math.max(0, Math.ceil((new Date(el.dataset.expires).getTime() - now) / 1000));
      el.textContent = left > 0 ? Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0") + " left" : "Settling…";
      if (left === 0) settle();
    });
  }
  if (timers.length) { tick(); setInterval(tick, 1000); }
})();
