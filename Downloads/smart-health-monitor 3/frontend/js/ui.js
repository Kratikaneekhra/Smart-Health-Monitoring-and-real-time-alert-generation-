// Small UI helpers shared by all views.
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function toast(msg, bad = false) {
  const el = document.createElement("div");
  el.className = "toast" + (bad ? " bad" : "");
  el.setAttribute("role", bad ? "alert" : "status");
  el.textContent = msg;
  document.getElementById("toast-root").append(el);
  setTimeout(() => el.remove(), 4200);
}

export const initials = (name) => name.replace("Dr. ", "").split(" ").map((p) => p[0]).slice(0, 2).join("");
export const inr = (n) => "₹" + Number(n).toLocaleString("en-IN");

export function dialog(html, onSubmit) {
  const d = document.getElementById("dlg");
  d.innerHTML = html;
  d.querySelector("[data-close]")?.addEventListener("click", () => d.close());
  d.querySelector("form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (e.submitter?.hasAttribute("data-close")) return d.close();
    await onSubmit(new FormData(e.target), d);
  });
  d.showModal();
  return d;
}
