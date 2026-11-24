import { api, ApiError, auth } from "./api.js";
import { dialog, esc, initials, inr, toast } from "./ui.js";

const KIDNEY_GROUPS = [
  ["Basics", ["age", "bp"]],
  ["Urine tests", ["sg", "al", "su", "rbc", "pc", "pcc", "ba"]],
  ["Blood tests", ["bgr", "bu", "sc", "sod", "pot", "hemo", "pcv", "wc", "rc"]],
  ["Medical history", ["htn", "dm", "cad", "appet", "pe", "ane"]],
];
const RESEARCH_ORDER = ["diabetes", "heart", "cardio", "kidney"];

/* =============================================================== HOME */
export async function homeView(root, ctx) {
  root.innerHTML = `
  <section class="hero">
    <svg class="trace" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 70 H160 l12 -8 l12 8 H300 l14 6 l16 -62 l20 98 l14 -42 H470 l14 -12 l22 12 H700 l12 -8 l12 8 H820 l14 6 l16 -62 l20 98 l14 -42 H1000 l14 -12 l22 12 H1200"/>
    </svg>
    <div class="wrap">
      <h1>Enter your readings. Get a risk report and the doctors to see.</h1>
      <p class="lead">Four machine-learning screenings for diabetes, heart disease, cardiovascular risk and kidney disease, followed by a ranked list of specialists matched to your results.</p>
      <div class="cta">
        <a class="btn" href="#/check">Start a health check</a>
        <a class="btn quiet" href="#/doctors">Browse doctors</a>
      </div>
    </div>
  </section>

  <section class="band"><div class="wrap">
    <h2>How a report is made</h2>
    <ol class="steps plain">
      <li><span class="n">Step 1</span><b>Enter your readings</b>Pick one screening or all four. Shared values such as age and blood pressure are copied between forms, and sample patients fill everything in for a quick demo.</li>
      <li><span class="n">Step 2</span><b>Models score your risk</b>Each screening runs the best of five trained models and shows which of your readings pushed the score up or down.</li>
      <li><span class="n">Step 3</span><b>Meet the right doctor</b>Your findings are matched against a doctor dataset by expertise, rating, experience and location, then ranked with the reasons shown.</li>
    </ol>
  </div></section>

  <section class="band" style="padding-top:0"><div class="wrap">
    <h2>What it screens</h2>
    <p class="muted">Models and inputs come from the research notebooks in this project.</p>
    <div class="table-scroll"><table class="table" id="screen-table">
      <thead><tr><th>Screening</th><th>Inputs</th><th>Looks at</th><th>Model in use</th><th>Specialist suggested</th></tr></thead>
      <tbody>${RESEARCH_ORDER.map((k) => {
        const d = ctx.state.schema.diseases[k];
        return `<tr><td><b>${esc(d.title)}</b></td><td>${d.fields.length}</td><td>${esc(d.summary)}</td><td data-model="${k}" class="muted">Loading</td><td>${esc(d.specialty)}</td></tr>`;
      }).join("")}</tbody>
    </table></div>
  </div></section>`;

  try {
    const m = await api.models();
    ctx.state.models = m;
    for (const k of RESEARCH_ORDER) {
      const td = root.querySelector(`[data-model="${k}"]`);
      const live = m.live[k];
      if (td && live) { td.textContent = live.deployed; td.classList.remove("muted"); }
    }
  } catch { /* the table still reads fine without it */ }
}

/* =============================================================== CHECK */
function fieldHtml(key, f) {
  const id = `${key}-${f.name}`;
  const label = `<label class="lbl" for="${id}">${esc(f.label)}${f.required ? "" : ' <span class="opt">(optional)</span>'}</label>`;
  const shared = `data-key="${key}" data-shared="${f.shared || ""}"`;
  const control = f.kind === "select"
    ? `<select class="in" id="${id}" name="${f.name}" ${shared}><option value="">${f.required ? "Choose" : "Not known"}</option>${
        f.options.map((o) => `<option value="${esc(o.value)}" data-tag="${o.tag || ""}">${esc(o.label)}</option>`).join("")}</select>`
    : `<div class="unit"><input class="in" type="number" inputmode="decimal" step="any" id="${id}" name="${f.name}" ${shared}
         placeholder="${f.min} to ${f.max}"><i>${esc(f.unit)}</i></div>`;
  return `<div class="field-row">${label}${control}${f.help ? `<div class="hint">${esc(f.help)}</div>` : ""}<div class="err" id="${id}-err" role="alert"></div></div>`;
}

function formCard(key, d) {
  const byName = Object.fromEntries(d.fields.map((f) => [f.name, f]));
  const body = key === "kidney"
    ? KIDNEY_GROUPS.map(([title, names]) => `<h3>${title}${title === "Basics" ? "" : " (all optional)"}</h3>${names.map((n) => fieldHtml(key, byName[n])).join("")}`).join("")
    : d.fields.map((f) => fieldHtml(key, f)).join("");
  return `<section class="sheet form-card" id="card-${key}" hidden>
    <header><h2>${esc(d.title)}</h2><span class="muted">Suggested specialist: ${esc(d.specialty)}</span></header>
    <div class="fields"><div class="form-error" id="${key}-form-err" hidden style="grid-column:1/-1"></div>${body}</div>
    ${key === "kidney" ? `<p class="hint" style="padding:0 24px 18px">Fill in at least ${d.min_filled} fields. The more lab values you add, the more reliable the result.</p>` : ""}
  </section>`;
}

export async function checkView(root, ctx) {
  const { diseases, cities } = ctx.state.schema;
  root.innerHTML = `
  <section class="page"><div class="wrap">
    <h1>Health check</h1>
    <p class="sub">Choose the screenings you want and enter your readings. You get one combined report with the doctors to see.</p>
    <div class="check">
      <aside class="side sheet pad">
        <h2>About you</h2>
        <div class="field-row"><label class="lbl" for="p-name">Name <span class="opt">(optional)</span></label><input class="in" id="p-name" autocomplete="name"></div>
        <div class="field-row"><label class="lbl" for="p-city">City for doctor search</label>
          <select class="in" id="p-city"><option value="">Any city</option>${cities.map((c) => `<option>${esc(c)}</option>`).join("")}</select></div>
        <div class="field-row"><label class="lbl" for="p-mode">Consultation type</label>
          <select class="in" id="p-mode"><option value="">Either</option><option value="In-person">In-person</option><option value="Teleconsult">Teleconsult</option></select></div>
        <h2 style="margin-top:22px">Screenings</h2>
        ${RESEARCH_ORDER.map((k) => `<label class="pick"><input type="checkbox" value="${k}"><div><b>${esc(diseases[k].title)}</b><span>${esc(diseases[k].summary)}</span></div></label>`).join("")}
        <div class="quick">
          <button type="button" class="btn quiet sm" data-sample="sample_high">Fill high-risk sample</button>
          <button type="button" class="btn quiet sm" data-sample="sample_low">Fill low-risk sample</button>
        </div>
        <button class="btn" id="go" style="width:100%;margin-top:10px">Generate report</button>
      </aside>
      <div id="forms">
        <div class="sheet empty" id="forms-empty">Tick a screening on the left to begin, or fill in a sample patient.</div>
        ${RESEARCH_ORDER.map((k) => formCard(k, diseases[k])).join("")}
      </div>
    </div>
  </div></section>`;

  const forms = root.querySelector("#forms");
  const picks = [...root.querySelectorAll(".pick input")];
  const selected = () => picks.filter((p) => p.checked).map((p) => p.value);
  const sync = () => {
    const s = selected();
    RESEARCH_ORDER.forEach((k) => (root.querySelector(`#card-${k}`).hidden = !s.includes(k)));
    root.querySelector("#forms-empty").hidden = s.length > 0;
  };
  picks.forEach((p) => p.addEventListener("change", sync));

  // Copy shared values (age, blood pressure, glucose, sex...) into the other forms unless the user typed there.
  const onEdit = (e) => {
    const el = e.target;
    if (!el.dataset.key) return;
    delete el.dataset.auto;
    el.removeAttribute("aria-invalid");
    root.querySelector(`#${el.id}-err`).textContent = "";
    const sh = el.dataset.shared;
    if (sh) {
      const tag = el.tagName === "SELECT" ? el.selectedOptions[0]?.dataset.tag : null;
      forms.querySelectorAll(`[data-shared="${sh}"]`).forEach((o) => {
        if (o === el || (o.value !== "" && !o.dataset.auto)) return;
        if (el.tagName === "SELECT") {
          const opt = tag && o.tagName === "SELECT" ? [...o.options].find((x) => x.dataset.tag === tag) : null;
          o.value = opt ? opt.value : "";
          if (opt) o.dataset.auto = 1;
        } else if (o.tagName === "INPUT") { o.value = el.value; o.dataset.auto = 1; }
      });
    }
    if (el.id === "cardio-height" || el.id === "cardio-weight") {  // BMI for the diabetes form
      const h = +root.querySelector("#cardio-height").value, w = +root.querySelector("#cardio-weight").value;
      const bmi = root.querySelector("#diabetes-bmi");
      if (h > 0 && w > 0 && (bmi.value === "" || bmi.dataset.auto)) { bmi.value = (w / (h / 100) ** 2).toFixed(1); bmi.dataset.auto = 1; }
    }
  };
  forms.addEventListener("input", onEdit);
  forms.addEventListener("change", onEdit);

  root.querySelectorAll("[data-sample]").forEach((b) => b.addEventListener("click", () => {
    for (const k of RESEARCH_ORDER) {
      for (const f of diseases[k].fields) {
        const el = root.querySelector(`#${k}-${f.name}`);
        el.value = String(diseases[k][b.dataset.sample][f.name] ?? "");
        delete el.dataset.auto;
        el.removeAttribute("aria-invalid");
        root.querySelector(`#${el.id}-err`).textContent = "";
      }
    }
    picks.forEach((p) => (p.checked = true));
    sync();
    toast(b.dataset.sample === "sample_high" ? "High-risk sample patient loaded." : "Low-risk sample patient loaded.");
  }));

  root.querySelector("#go").addEventListener("click", async (ev) => {
    const keys = selected();
    if (!keys.length) return toast("Tick at least one screening first.", true);
    root.querySelectorAll(".err").forEach((e) => (e.textContent = ""));
    root.querySelectorAll("[aria-invalid]").forEach((e) => e.removeAttribute("aria-invalid"));
    root.querySelectorAll(".form-error").forEach((e) => (e.hidden = true));
    const assessments = {};
    for (const k of keys) {
      assessments[k] = {};
      for (const f of diseases[k].fields) {
        const v = root.querySelector(`#${k}-${f.name}`).value;
        if (v !== "") assessments[k][f.name] = v;
      }
    }
    const btn = ev.currentTarget;
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Analysing';
    try {
      const rep = await api.report({
        patient: { name: root.querySelector("#p-name").value, city: root.querySelector("#p-city").value, mode: root.querySelector("#p-mode").value },
        assessments,
      });
      ctx.setReport(rep);
      location.hash = "#/report";
    } catch (e) {
      if (e instanceof ApiError && e.fields) {
        let first = null;
        for (const [k, errs] of Object.entries(e.fields)) {
          for (const [name, msg] of Object.entries(errs)) {
            if (name === "_form") {
              const box = root.querySelector(`#${k}-form-err`); box.textContent = msg; box.hidden = false; first ||= box; continue;
            }
            const el = root.querySelector(`#${k}-${name}`);
            if (el) { el.setAttribute("aria-invalid", "true"); root.querySelector(`#${k}-${name}-err`).textContent = msg; first ||= el; }
          }
        }
        toast("Some values need attention. See the highlighted fields.", true);
        first?.scrollIntoView({ block: "center" });
        if (first?.focus) first.focus({ preventScroll: true });
      } else toast(e.message, true);
      btn.disabled = false; btn.textContent = "Generate report";
    }
  });
}

/* =============================================================== REPORT */
const ruler = (r) => {
  const [t1, t2] = r.thresholds.map((x) => x * 100);
  const p = Math.max(1, Math.min(99, r.percent));
  const shift = p < 6 ? 12 : p > 94 ? 88 : 50;
  return `<div class="ruler-box"><div class="ruler" role="img" aria-label="${r.percent} percent probability, ${r.risk_level} risk">
    <div class="z low" style="width:${t1}%"></div><div class="z mod" style="width:${t2 - t1}%"></div><div class="z high" style="width:${100 - t2}%"></div>
    <div class="marker" data-to="${p}"><b style="transform:translateX(-${shift}%)">${r.percent}%</b></div></div>
    <div class="scale"><span style="width:${t1}%">Low</span><span style="width:${t2 - t1}%">Moderate</span><span style="width:${100 - t2}%">High</span></div></div>`;
};

const factorList = (items, down) => items.length
  ? `<ul class="bars">${items.map((f) => `<li><span>${esc(f.label)}<em>${esc(f.value)}</em></span><span class="bar ${down ? "down" : ""}"><i data-w="${Math.max(8, Math.round(f.strength * 100))}"></i></span></li>`).join("")}</ul>`
  : `<p class="muted" style="font-size:14.5px">Nothing stands out.</p>`;

export function docCard(d, { book = true } = {}) {
  const spec = d.specialization.replace(/ /g, "");
  return `<article class="doc sheet">
    <div class="avatar av-${spec}" aria-hidden="true">${esc(initials(d.name))}</div>
    <div>
      <h4>${esc(d.name)}</h4>
      <div class="line">${esc(d.specialization)}, ${esc(d.qualification)}</div>
      <div class="line">${esc(d.hospital)}, ${esc(d.city)}</div>
      <div class="chips"><span class="chip">${d.experience_years} years</span><span class="chip">Rated ${Number(d.rating).toFixed(1)}</span><span class="chip">${inr(d.consultation_fee_inr)}</span><span class="chip">${esc(d.mode)}</span><span class="chip">${esc(d.available_days)}</span></div>
      ${d.reasons ? `<ul class="why">${d.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
    </div>
    <div class="side-col">
      ${d.match_percent != null ? `<div class="match">${d.match_percent}%<small>match</small></div>` : ""}
      ${book ? `<button class="btn sm ghost" data-book="${esc(d.doctor_id)}" data-name="${esc(d.name)}">Request appointment</button>` : ""}
    </div></article>`;
}

export function wireBooking(root, ctx, reportId) {
  root.querySelectorAll("[data-book]").forEach((b) => b.addEventListener("click", () => {
    if (!ctx.state.user) {
      return dialog(`<form method="dialog"><h3>Sign in first</h3><p class="muted">Appointment requests are saved to your account so you can track them.</p>
        <div class="dlg-actions"><button class="btn quiet" data-close>Not now</button><a class="btn" href="#/login" onclick="document.getElementById('dlg').close()">Sign in</a></div></form>`, () => {});
    }
    const today = new Date().toISOString().slice(0, 10);
    dialog(`<form><h3>Request appointment</h3><p class="muted">${esc(b.dataset.name)}</p>
      <div class="field-row"><label class="lbl" for="ap-date">Preferred date</label><input class="in" type="date" id="ap-date" name="date" min="${today}" required></div>
      <div class="field-row"><label class="lbl" for="ap-note">Note for the clinic <span class="opt">(optional)</span></label><textarea class="in" id="ap-note" name="note" rows="3" maxlength="300"></textarea></div>
      <div class="dlg-actions"><button type="button" class="btn quiet" data-close>Cancel</button><button class="btn">Send request</button></div></form>`,
    async (fd, d) => {
      try {
        const r = await api.book({ doctor_id: b.dataset.book, doctor_name: b.dataset.name, preferred_date: fd.get("date"), note: fd.get("note"), report_id: reportId });
        d.close(); toast(r.message);
      } catch (e) { toast(e.message, true); }
    });
  }));
}

export async function reportView(root, ctx) {
  const rep = ctx.state.report;
  if (!rep) {
    root.innerHTML = `<section class="page"><div class="wrap"><div class="sheet empty">No report yet. <a href="#/check">Start a health check</a> to create one.</div></div></section>`;
    return;
  }
  const demo = rep.results.some((r) => r.model.data_source === "demo-synthetic");
  root.innerHTML = `
  <section class="page"><div class="wrap">
    <div class="rep-head">
      <div><h1>Health report${rep.patient.name ? ` for ${esc(rep.patient.name)}` : ""}</h1>
        <div class="meta">Report ${esc(rep.report_id)}, created ${esc(rep.created)}${rep.saved ? ", saved to your account" : ""}</div></div>
      <div class="actions no-print">
        <button class="btn" id="pdf">Download PDF</button>
        <button class="btn quiet" id="print">Print</button>
        <a class="btn quiet" href="#/check">New check</a>
      </div>
    </div>
    ${demo ? `<div class="notice no-print" style="margin-bottom:18px"><b>Demo models.</b> This build was trained on synthetic data, so the numbers below show how the system works and are not medical results. Retrain with your real datasets (see the README).</div>` : ""}
    ${!rep.saved ? `<div class="notice info no-print" style="margin-bottom:18px">You are using the app as a guest. <a href="#/login">Sign in</a> before generating a report to keep it in My reports.</div>` : ""}

    <div class="overall lv-${rep.overall.level}"><h2>${esc(rep.overall.headline)}</h2><p>${esc(rep.overall.detail)}</p></div>

    ${rep.results.map((r) => `
    <article class="sheet res lv-${r.risk_level}">
      <header><h2>${esc(r.title)}</h2><span class="tag">${r.risk_level} model risk</span></header>
      ${ruler(r)}
      <div class="res-body">
        <div>
          <h3>Factors increasing model prediction</h3>${factorList(r.factors_up, false)}
          ${r.factors_down.length ? `<h3>Factors decreasing model prediction</h3>${factorList(r.factors_down, true)}` : ""}
          ${r.flags.length ? `<h3>What your readings show</h3><ul class="flags">${r.flags.map((f) => `<li class="${f.level}">${esc(f.text)}</li>`).join("")}</ul>` : ""}
        </div>
        <div>
          <h3>Suggested next steps</h3>
          <p><b>${esc(r.urgency)}</b> Suggested specialist: ${esc(r.specialty)}.</p>
          <ul class="tips">${r.advice.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>
        </div>
      </div>
      <div class="foot-note">Model: ${esc(r.model.name)}, ROC-AUC ${r.model.roc_auc.toFixed(2)} on held-out test data, trained on ${r.model.n_train.toLocaleString()} records${r.model.data_source === "demo-synthetic" ? " (synthetic demo data)" : ""}. Bars show a reference-value occlusion comparison, not causal effects or SHAP values.</div>
    </article>`).join("")}

    <h2 style="font-size:28px;margin:34px 0 4px">Doctors to see</h2>
    <p class="muted" style="margin-bottom:18px">Ranked by how well their expertise matches your findings, plus rating, experience and ${rep.patient.city ? `distance from ${esc(rep.patient.city)}` : "availability"}.</p>
    ${rep.doctor_groups.map((g) => `
      <div class="group lv-${g.risk_level}">
        <h3>${esc(g.specialty)}</h3>
        <p><b>${esc(g.urgency)}</b> ${esc(g.reasons.join("; "))}.</p>
        ${g.doctors.map((d) => docCard(d)).join("")}
      </div>`).join("")}

    <div class="notice" style="margin-top:26px"><b>Emergency.</b> ${esc(rep.emergency)}</div>
  </div></section>`;

  // Animate the risk markers and factor bars once the page is on screen.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    root.querySelectorAll(".marker").forEach((m) => (m.style.left = m.dataset.to + "%"));
    root.querySelectorAll(".bar i").forEach((i) => (i.style.width = i.dataset.w + "%"));
  }));
  root.querySelector("#print").addEventListener("click", () => window.print());
  root.querySelector("#pdf").addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    try {
      const blob = await (await api.pdf(rep)).blob();
      const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `health-report-${rep.report_id}.pdf` });
      a.click(); URL.revokeObjectURL(a.href);
    } catch (err) { toast(err.message, true); }
    e.currentTarget.disabled = false;
  });
  wireBooking(root, ctx, rep.report_id);
}
