import { api, auth } from "./api.js";
import { esc, toast } from "./ui.js";
import { checkView, homeView, reportView } from "./views.js";
import { doctorsView, historyView, loginView, modelsView } from "./pages.js";

const state = { schema: null, user: null, report: null, models: null };
try { state.report = JSON.parse(sessionStorage.getItem("shm_report")); } catch { /* none stored */ }

const ctx = {
  state,
  setReport(r) { state.report = r; try { sessionStorage.setItem("shm_report", JSON.stringify(r)); } catch { /* ignore */ } },
  setUser(u) { state.user = u; drawUser(); },
};

const routes = { "": homeView, check: checkView, report: reportView, doctors: doctorsView, models: modelsView, history: historyView, login: loginView };
const app = document.getElementById("app");

function drawUser() {
  const who = document.getElementById("who");
  if (state.user) {
    who.innerHTML = `<span>${esc(state.user.name)}</span><button class="btn quiet sm" id="out">Sign out</button>`;
    document.getElementById("out").addEventListener("click", () => { auth.token = null; ctx.setUser(null); toast("Signed out."); location.hash = "#/"; });
  } else who.innerHTML = `<a class="btn ghost sm" href="#/login">Sign in</a>`;
}

async function render() {
  const route = location.hash.replace(/^#\/?/, "").split("?")[0];
  document.querySelectorAll("#nav a").forEach((a) => {
    const on = a.dataset.r === route || (route === "report" && a.dataset.r === "check");
    on ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
  });
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  app.innerHTML = "";
  await (routes[route] || homeView)(app, ctx);
  window.scrollTo(0, 0);
}

async function boot() {
  try {
    state.schema = await api.schema();
  } catch (e) {
    app.innerHTML = `<section class="page"><div class="wrap"><div class="sheet empty"><b>${esc(e.message)}</b><br>Start the server with <code>python run.py</code> and reload.</div></div></section>`;
    return;
  }
  if (auth.token) { try { state.user = (await api.me()).user; } catch { auth.token = null; } }
  drawUser();
  window.addEventListener("hashchange", render);
  render();
}
boot();
