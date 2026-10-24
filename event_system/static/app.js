"use strict";
const $ = (id) => document.getElementById(id);
const state = { user: null, myRegs: new Set(), categories: [] };

/* ---------- Köməkçi funksiyalar ---------- */
function esc(s) {                      // XSS-dən qorunma: istifadəçi mətni HTML kimi icra olunmur
  const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML;
}
function toast(msg, type = "ok") {
  const t = $("toast"); t.textContent = msg; t.className = type; t.style.display = "block";
  clearTimeout(toast.timer); toast.timer = setTimeout(() => (t.style.display = "none"), 3500);
}
async function api(path, method = "GET", body) {
  try {
    const res = await fetch("/api" + path, {
      method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Xəta baş verdi.");
    return data;
  } catch (e) {
    if (e instanceof TypeError) throw new Error("Serverlə əlaqə qurulmadı.");
    throw e;
  }
}
const guard = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, "error"); } };

/* ---------- Naviqasiya ---------- */
document.querySelectorAll("nav button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
function showTab(name) {
  document.querySelectorAll("main > section").forEach((s) => (s.hidden = s.id !== "tab-" + name));
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  if (name === "dashboard") loadStats().catch((e) => toast(e.message, "error"));
  if (name === "form" && !$("eId").value) resetForm();
}

/* ---------- Giriş ---------- */
function renderUser() {
  $("userBox").innerHTML = state.user
    ? `${esc(state.user.full_name)} <button class="secondary" id="logout">Çıxış</button>` : "";
  if (state.user) $("logout").onclick = () => { localStorage.removeItem("user"); location.reload(); };
}
$("lGo").onclick = guard(async () => {
  $("lErr").textContent = "";
  try {
    state.user = await api("/login", "POST", { full_name: $("lName").value, email: $("lEmail").value });
  } catch (e) { $("lErr").textContent = e.message; return; }
  localStorage.setItem("user", JSON.stringify(state.user));
  $("loginDlg").close(); await start();
});

/* ---------- Tədbir siyahısı ---------- */
async function loadEvents() {
  const p = new URLSearchParams();
  [["q", "fQ"], ["category_id", "fCat"], ["location", "fLoc"], ["date_from", "fFrom"], ["date_to", "fTo"]]
    .forEach(([k, id]) => $(id).value && p.set(k, $(id).value));
  const events = await api("/events?" + p);
  if (state.user) state.myRegs = new Set(await api(`/users/${state.user.id}/registrations`));
  $("eventList").innerHTML = events.length
    ? events.map(eventCard).join("")
    : `<div class="empty">Axtarışa uyğun tədbir tapılmadı.</div>`;
}
function eventCard(e) {
  const pct = Math.min(100, Math.round((e.registered / e.capacity) * 100));
  const mine = state.myRegs.has(e.id);
  const action = mine
    ? `<button class="secondary" data-act="cancel" data-id="${e.id}">Qeydiyyatı ləğv et</button>`
    : `<button data-act="register" data-id="${e.id}" ${e.is_past || e.is_full ? "disabled" : ""}>${
        e.is_past ? "Keçib" : e.is_full ? "Yer qalmayıb" : "Qeydiyyatdan keç"}</button>`;
  return `<article class="card">
    <div><span class="badge ${e.is_past ? "past" : "upcoming"}">${e.is_past ? "Keçmiş" : "Gələcək"}</span>
         <span class="badge">${esc(e.category)}</span> ${mine ? '<span class="badge upcoming">✓ Qeydiyyatdayam</span>' : ""}</div>
    <h3>${esc(e.title)}</h3>
    <div class="meta">📅 ${esc(e.event_date)} ${esc(e.event_time)} · 📍 ${esc(e.location)}</div>
    <p>${esc(e.description)}</p>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="meta">${e.registered} / ${e.capacity} iştirakçı</div>
    <div class="actions">${action}
      <button class="secondary" data-act="people" data-id="${e.id}">İştirakçılar</button>
      <button class="secondary" data-act="edit" data-id="${e.id}">Redaktə</button>
      <button class="danger" data-act="delete" data-id="${e.id}">Sil</button></div>
  </article>`;
}
$("eventList").onclick = guard(async (ev) => {
  const btn = ev.target.closest("button[data-act]"); if (!btn) return;
  const id = Number(btn.dataset.id), uid = state.user.id;
  switch (btn.dataset.act) {
    case "register": await api(`/events/${id}/register`, "POST", { user_id: uid }); toast("Qeydiyyat uğurla tamamlandı."); break;
    case "cancel": await api(`/events/${id}/cancel`, "POST", { user_id: uid }); toast("Qeydiyyat ləğv edildi."); break;
    case "delete": if (!confirm("Tədbir və onun bütün qeydiyyatları silinəcək. Əminsiniz?")) return;
      await api(`/events/${id}`, "DELETE"); toast("Tədbir silindi."); break;
    case "edit": return fillForm(await api(`/events/${id}`));
    case "people": return showParticipants(id);
  }
  await loadEvents();
});
async function showParticipants(id) {
  const [e, list] = [await api(`/events/${id}`), await api(`/events/${id}/participants`)];
  $("partTitle").textContent = `${e.title} — ${list.length} iştirakçı`;
  $("partList").innerHTML = list.length ? list.map((u) => `<li>${esc(u.full_name)} (${esc(u.email)})</li>`).join("") : "<li>Hələ qeydiyyat yoxdur.</li>";
  $("partDlg").showModal();
}
["fQ", "fLoc"].forEach((id) => $(id).addEventListener("input", guard(loadEvents)));
["fCat", "fFrom", "fTo"].forEach((id) => $(id).addEventListener("change", guard(loadEvents)));
$("fReset").onclick = guard(async () => { ["fQ", "fCat", "fLoc", "fFrom", "fTo"].forEach((i) => ($(i).value = "")); await loadEvents(); });

/* ---------- Tədbir formu ---------- */
const FIELDS = { eTitle: "title", eCat: "category_id", eDate: "event_date", eTime: "event_time", eLoc: "location", eCap: "capacity", eDesc: "description" };
function resetForm() { $("eId").value = ""; Object.keys(FIELDS).forEach((i) => ($(i).value = "")); $("formTitle").textContent = "Yeni tədbir"; }
function fillForm(e) {
  showTab("form"); $("eId").value = e.id; $("formTitle").textContent = "Tədbiri redaktə et";
  Object.entries(FIELDS).forEach(([id, key]) => ($(id).value = e[key]));
}
$("eCancel").onclick = () => { resetForm(); showTab("events"); };
$("eSave").onclick = guard(async () => {
  const body = Object.fromEntries(Object.entries(FIELDS).map(([id, key]) => [key, $(id).value]));
  const id = $("eId").value;
  await api(id ? `/events/${id}` : "/events", id ? "PUT" : "POST", body);
  toast(id ? "Tədbir yeniləndi." : "Tədbir yaradıldı.");
  resetForm(); showTab("events"); await loadEvents();
});

/* ---------- Statistika ---------- */
function bars(rows, label, value, max) {
  return rows.length ? rows.map((r) => `<div class="row"><span>${esc(r[label])}</span>
    <div class="bar"><i style="width:${max ? (r[value] / max) * 100 : 0}%"></i></div><b>${r[value]}</b></div>`).join("")
    : "<p class='meta'>Məlumat yoxdur.</p>";
}
async function loadStats() {
  const s = await api("/stats");
  $("cards").innerHTML = [["Tədbirlər", s.total_events], ["Qeydiyyatlar", s.total_registrations], ["İstifadəçilər", s.total_users]]
    .map(([l, n]) => `<div class="stat"><b>${n}</b>${l}</div>`).join("");
  $("topChart").innerHTML = bars(s.top_events, "title", "registered", Math.max(1, ...s.top_events.map((x) => x.registered)));
  $("catChart").innerHTML = bars(s.by_category, "category", "events", Math.max(1, ...s.by_category.map((x) => x.events)));
}

/* ---------- Başlanğıc ---------- */
async function start() {
  renderUser();
  state.categories = await api("/categories");
  const opts = state.categories.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  $("fCat").innerHTML = '<option value="">Bütün kateqoriyalar</option>' + opts;
  $("eCat").innerHTML = '<option value="">Seçin…</option>' + opts;
  await loadEvents();
}
(async function init() {
  try { state.user = JSON.parse(localStorage.getItem("user")); } catch { state.user = null; }
  if (!state.user) { $("loginDlg").showModal(); return; }
  await start().catch((e) => toast(e.message, "error"));
})();
