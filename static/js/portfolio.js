(function () {
  if (!document.querySelector("[data-pf]")) return;
  const fmt = (n) => n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sign = (n) => (n >= 0 ? "+" : "");

  function setText(name, text) {
    document.querySelectorAll('[data-pf="' + name + '"]').forEach((el) => (el.textContent = text));
  }

  async function refresh() {
    try {
      const res = await fetch("/api/portfolio");
      if (!res.ok) return;
      const d = await res.json();
      setText("total", fmt(d.total));
      setText("cash", fmt(d.cash));
      setText("btc_value", fmt(d.btc_value));
      setText("eth_value", fmt(d.eth_value));
      setText("btc_units", d.btc_units.toFixed(6));
      setText("eth_units", d.eth_units.toFixed(6));
      document.querySelectorAll('[data-pf="change"]').forEach((el) => {
        if (!d.has_holdings || !d.price_ok) return;
        el.textContent = sign(d.change) + d.change.toFixed(2) + " USDT (" + sign(d.change_pct) +
          d.change_pct.toFixed(2) + "%) since added";
        el.classList.toggle("up", d.change >= 0);
        el.classList.toggle("down", d.change < 0);
      });
    } catch (_) { /* keep what is on screen */ }
  }
  setInterval(refresh, 30000);
})();
