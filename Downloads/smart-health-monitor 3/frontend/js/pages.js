import { api, auth } from "./api.js";
import { docCard, wireBooking } from "./views.js";
import { esc, toast } from "./ui.js";

/* =============================================================== DOCTORS */
export async function doctorsView(root, ctx) {
  const cities = ctx.state.schema.cities;
  root.innerHTML = `<section class="page"><div class="wrap">
    <h1>Doctor directory</h1>
    <p class="sub">The doctor dataset behind the recommendations. Search it directly, or generate a report to see doctors ranked for your findings.</p>
    <div class="sheet filters no-print">
      <div><label class="lbl" for="f-q">Search</label><input class="in" id="f-q" placeholder="Name, hospital or condition"></div>
      <div><label class="lbl" for="f-s">Specialty</label><select class="in" id="f-s"><option value="">All</option>
        ${["Endocrinologist", "Cardiologist", "Nephrologist", "General Physician"].map((s) => `<option>${s}</option>`).join("")}</select></div>
      <div><label class="lbl" for="f-c">City</label><select class="in" id="f-c"><option value="">All</option>${cities.map((c) => `<option>${esc(c)}</option>`).join("")}</select></div>
      <div><label class="lbl" for="f-m">Consultation</label><select class="in" id="f-m"><option value="">Any</option><option>In-person</option><option>Teleconsult</option></select></div>
      <div><label class="lbl" for="f-o">Sort by</label><select class="in" id="f-o"><option value="rating">Highest rated</option><option value="experience">Most experienced</option><option value="fee">Lowest fee</option></select></div>
    </div>
    <p class="muted" id="count" aria-live="polite"></p><div id="list"></div></div></section>`;
  const q = (id) => root.querySelector(id);
  let timer;
  const load = async () => {
    try {
      const { doctors } = await api.doctors({ q: q("#f-q").value, specialization: q("#f-s").value, city: q("#f-c").value, mode: q("#f-m").value, sort: q("#f-o").value });
      q("#count").textContent = `${doctors.length} doctor${doctors.length === 1 ? "" : "s"} found`;
      q("#list").innerHTML = doctors.length ? doctors.map((d) => docCard(d)).join("") : `<div class="sheet empty">No doctors match these filters. Try another city or clear the search.</div>`;
      wireBooking(root, ctx, null);
    } catch (e) { toast(e.message, true); }
  };
  root.querySelectorAll("select").forEach((s) => s.addEventListener("change", load));
  q("#f-q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
  load();
}

/* =============================================================== MODELS */
const pct = (v) => (v * 100).toFixed(1) + "%";
export async function modelsView(root, ctx) {
  root.innerHTML = `<section class="page"><div class="wrap"><h1>Models</h1><p class="sub">Loading</p></div></section>`;
  let data;
  try { data = await api.models(); } catch (e) { root.querySelector(".sub").textContent = e.message; return; }
  const demo = Object.values(data.live).some((l) => l.data_source === "demo-synthetic");
  root.innerHTML = `<section class="page"><div class="wrap">
    <h1>Models and results</h1>
    <p class="sub">For every screening, five models were trained and compared on a held-out 20 percent test set. The best by ROC-AUC is deployed in the app. Tables below are the results from your research notebooks.</p>\n    <div class="notice info" style="margin-bottom:18px"><b>Educational demo only:</b> The bundled deployed models use synthetic/demo data. Scores are model outputs, not validated clinical probabilities or diagnoses. Explanations do not show causation. The doctor directory is fictional.</div>
    <div class="pipeline" style="margin-bottom:26px">
      <div><b>Clean</b>Remove duplicates, impossible values and zero placeholders.</div>
      <div><b>Prepare</b>Median or mode imputation, scaling, one-hot encoding.</div>
      <div><b>Compare</b>Logistic Regression, Decision Tree, Random Forest, XGBoost, ANN.</div>
      <div><b>Select</b>Best test ROC-AUC is saved as the deployed pipeline.</div>
      <div><b>Explain</b>Each reading is swapped for a healthy value to see its effect.</div>
    </div>
    ${demo ? `<div class="notice" style="margin-bottom:22px"><b>Demo models in this build.</b> The deployed models were trained on synthetic data so the project runs without your datasets. Copy your CSV files into <code>data/raw/</code> and run <code>python ml/train_models.py</code> to deploy models trained on real data.</div>` : ""}
    ${["diabetes", "heart", "cardio", "kidney"].map((k) => {
      const r = data.research[k], live = data.live[k];
      return `<section class="sheet m-block"><header><h2>${esc(data.titles[k])}</h2>
        <span class="muted">${esc(r.dataset)}</span></header>
        <p class="muted" style="padding:0 24px;font-size:14.5px">${esc(r.split)}. ${live ? `Deployed in this app: <b>${esc(live.deployed)}</b> (${live.data_source === "demo-synthetic" ? "synthetic demo data" : "your data"}, ${live.n_train.toLocaleString()} training records).` : ""}</p>
        <div class="table-scroll"><table class="table" style="border:0;border-radius:0"><thead><tr><th>Model</th><th>ROC-AUC</th><th>Recall</th><th>Precision</th><th>Specificity</th><th>F1</th><th>Accuracy</th></tr></thead><tbody>
        ${r.models.map((m) => `<tr class="${m.model === r.best ? "best" : ""}"><td>${esc(m.model)}${m.model === r.best ? " (best)" : ""}</td>
          <td><span class="auc" style="width:${Math.max(4, Math.round((m.roc_auc - 0.5) * 2 * 80))}px"></span>${m.roc_auc.toFixed(3)}</td>
          <td>${pct(m.recall)}</td><td>${pct(m.precision)}</td><td>${pct(m.specificity)}</td><td>${m.f1.toFixed(3)}</td><td>${pct(m.accuracy)}</td></tr>`).join("")}
        </tbody></table></div></section>`;
    }).join("")}
    <div class="notice info">Recall is the share of people who truly have the disease that the model catches. For screening, recall matters most because a missed case costs more than a false alarm. The kidney dataset has only 400 patients, so its near-perfect scores should be read with caution.</div>
  </div></section>`;
}

/* =============================================================== HISTORY */
export async function historyView(root, ctx) {
  if (!ctx.state.user) {
    root.innerHTML = `<section class="page"><div class="wrap"><h1>My reports</h1><div class="sheet empty">Sign in to see your saved reports and appointment requests.<br><br><a class="btn" href="#/login">Sign in</a></div></div></section>`;
    return;
  }
  root.innerHTML = `<section class="page"><div class="wrap"><h1>My reports</h1><p class="sub">Loading</p></div></section>`;
  try {
    const { reports, appointments } = await api.history();
    root.innerHTML = `<section class="page"><div class="wrap"><h1>My reports</h1>
      <p class="sub">Reports are saved automatically when you are signed in.</p>
      <div class="sheet" style="margin-bottom:30px">${reports.length ? reports.map((r) => `
        <div class="hist-row"><div><b>${esc(r.summary)}</b><div class="meta">${esc(r.id)}, ${esc(r.created)} UTC, ${esc(r.diseases.join(", "))}</div></div>
        <button class="btn quiet sm" data-open="${esc(r.id)}">Open</button></div>`).join("") : `<div class="empty">No reports yet. <a href="#/check">Start a health check</a>.</div>`}</div>
      <h2 style="font-size:24px;margin-bottom:12px">Appointment requests</h2>
      ${appointments.length ? `<div class="table-scroll"><table class="table"><thead><tr><th>Doctor</th><th>Specialty</th><th>Hospital</th><th>Preferred date</th><th>Status</th></tr></thead><tbody>
        ${appointments.map((a) => `<tr><td>${esc(a.doctor_name)}</td><td>${esc(a.specialization)}</td><td>${esc(a.hospital)}</td><td>${esc(a.preferred_date)}</td><td>${esc(a.status)}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="sheet empty">No appointment requests yet.</div>`}</div></section>`;
    root.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", async () => {
      try { ctx.setReport(await api.savedReport(b.dataset.open)); location.hash = "#/report"; } catch (e) { toast(e.message, true); }
    }));
  } catch (e) { toast(e.message, true); }
}

/* =============================================================== LOGIN */
export function loginView(root, ctx) {
  let mode = "login";
  const draw = () => {
    root.innerHTML = `<section class="page"><div class="wrap"><div class="auth sheet pad">
      <h1>${mode === "login" ? "Sign in" : "Create account"}</h1>
      <form id="af" novalidate>
        ${mode === "register" ? `<div class="field-row"><label class="lbl" for="a-name">Name</label><input class="in" id="a-name" autocomplete="name" required></div>` : ""}
        <div class="field-row"><label class="lbl" for="a-email">Email</label><input class="in" id="a-email" type="email" autocomplete="email" required></div>
        <div class="field-row"><label class="lbl" for="a-pw">Password</label><input class="in" id="a-pw" type="password" autocomplete="${mode === "login" ? "current-password" : "new-password"}" minlength="6" required>
          ${mode === "register" ? `<div class="hint">At least 6 characters.</div>` : ""}</div>
        <div class="err" id="a-err" role="alert"></div>
        <button class="btn" style="width:100%;margin-top:8px">${mode === "login" ? "Sign in" : "Create account"}</button>
      </form>
      <p style="margin:18px 0 0;font-size:14.5px">${mode === "login" ? "New here?" : "Already registered?"}
        <button class="link" id="sw">${mode === "login" ? "Create an account" : "Sign in"}</button></p></div></div></section>`;
    root.querySelector("#sw").addEventListener("click", () => { mode = mode === "login" ? "register" : "login"; draw(); });
    root.querySelector("#af").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = { email: root.querySelector("#a-email").value, password: root.querySelector("#a-pw").value };
      if (mode === "register") body.name = root.querySelector("#a-name").value;
      try {
        const r = await (mode === "login" ? api.login(body) : api.register(body));
        auth.token = r.token; ctx.setUser(r.user);
        toast(`Welcome, ${r.user.name}.`);
        location.hash = "#/check";
      } catch (err) { root.querySelector("#a-err").textContent = err.message; }
    });
  };
  draw();
}
