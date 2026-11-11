"use strict";

/* ------------------------------------------------------------------ */
/* Testi dell'interfaccia                                               */
/* ------------------------------------------------------------------ */
const UI = {
  it: {
    loginHint: "Inserisci il codice che hai scelto durante l'installazione.",
    pin: "Codice", open: "Apri", wrongPin: "Codice sbagliato. Riprova.", tooMany: "Troppi tentativi. Riprova tra 10 minuti.",
    nextExams: "Prossimi compiti in classe", seeAll: "Calendario", tabNew: "Novità", tabAll: "Tutte", tabExams: "Compiti",
    updated: "Aggiornato alle", loading: "Carico le comunicazioni…",
    nothingNew: "Tutto letto", nothingNewSub: "Nessuna comunicazione nuova dal portale.",
    noExams: "Nessun compito in classe in programma.", needs: "da confermare", toVote: "da votare", newTag: "nuova",
    confirm: "Segna come ricevuto", confirmed: "Ricevuto confermato sul portale", markRead: "Segna come letto", markedRead: "Segnata come letta",
    vote: "Apri il sondaggio", sendVote: "Invia la risposta", voted: "Risposta inviata al portale", alreadyVoted: "Hai già risposto il",
    pollClosed: "Il sondaggio è chiuso o non accetta più risposte.", pollEnds: "Scade il", showOriginal: "Mostra testo originale (tedesco)",
    hideOriginal: "Mostra traduzione", attachments: "Allegati", from: "Da", classes: "Classi",
    confirmSend: "Confermi l'invio? La risposta va direttamente al portale della scuola e di solito non si può modificare.",
    yesSend: "Sì, invia", cancel: "Annulla", pickAnswer: "Scegli almeno una risposta.",
    errNetwork: "Il portale non risponde. Controlla la connessione e tocca Aggiorna.",
    errPortalLogin: "Il connettore non riesce ad accedere all'Eltern-Portal: controlla email e password nelle impostazioni del server.",
    partial: "Alcune sezioni non si sono caricate:", allCats: "Tutte", inDays: (n) => n === 0 ? "oggi" : n === 1 ? "domani" : `tra ${n} giorni`,
    daysAgo: (n) => n === 1 ? "ieri" : `${n} giorni fa`, showPast: "Mostra anche quelli passati", hidePast: "Nascondi quelli passati",
    addCal: "Aggiungi al calendario del telefono", schulaufgabe: "Compito in classe", test: "Verifica breve", altro: "Prova",
    newCount: (n) => n === 1 ? "1 nuova" : `${n} nuove`, logout: "Esci",
    sendError: "Invio non riuscito:",
  },
  en: {
    loginHint: "Enter the code you chose during setup.",
    pin: "Code", open: "Open", wrongPin: "Wrong code. Try again.", tooMany: "Too many attempts. Try again in 10 minutes.",
    nextExams: "Upcoming exams", seeAll: "Calendar", tabNew: "New", tabAll: "All", tabExams: "Exams",
    updated: "Updated at", loading: "Loading messages…",
    nothingNew: "All caught up", nothingNewSub: "No new messages on the portal.",
    noExams: "No exams scheduled.", needs: "to confirm", toVote: "to vote", newTag: "new",
    confirm: "Mark as received", confirmed: "Receipt confirmed on the portal", markRead: "Mark as read", markedRead: "Marked as read",
    vote: "Open poll", sendVote: "Send answer", voted: "Answer sent to the portal", alreadyVoted: "You answered on",
    pollClosed: "This poll is closed or no longer accepts answers.", pollEnds: "Closes on", showOriginal: "Show original text (German)",
    hideOriginal: "Show translation", attachments: "Attachments", from: "From", classes: "Classes",
    confirmSend: "Send this answer? It goes straight to the school portal and usually can't be changed.",
    yesSend: "Yes, send", cancel: "Cancel", pickAnswer: "Pick at least one answer.",
    errNetwork: "The portal isn't responding. Check your connection and tap Refresh.",
    errPortalLogin: "The connector can't sign in to Eltern-Portal: check the email and password in the server settings.",
    partial: "Some sections didn't load:", allCats: "All", inDays: (n) => n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${n} days`,
    daysAgo: (n) => n === 1 ? "yesterday" : `${n} days ago`, showPast: "Show past ones too", hidePast: "Hide past ones",
    addCal: "Add to phone calendar", schulaufgabe: "Exam", test: "Short test", altro: "Assessment",
    newCount: (n) => `${n} new`, logout: "Sign out",
    sendError: "Couldn't send:",
  },
};
const CATS = {
  elternbriefe: { it: "Lettere ai genitori", en: "Parent letters", c: "var(--ink)" },
  umfragen: { it: "Sondaggi", en: "Polls", c: "var(--green)" },
  klassenleitung: { it: "Messaggi dal coordinatore di classe", en: "Messages from class teacher", c: "var(--violet)" },
  fachlehrer: { it: "Messaggi dai professori", en: "Messages from teachers", c: "var(--violet)" },
  schwarzes_brett: { it: "Bacheca", en: "Notice board", c: "var(--muted)" },
};
const TOPICS = {
  verifiche: { it: "Verifiche e voti", en: "Tests & grades" },
  gite: { it: "Gite e uscite", en: "Trips" },
  eventi: { it: "Incontri ed eventi", en: "Meetings & events" },
  pagamenti: { it: "Pagamenti", en: "Payments" },
  salute: { it: "Salute", en: "Health" },
  orari: { it: "Orari e giorni liberi", en: "Schedule & days off" },
  elezioni: { it: "Elezioni e votazioni", en: "Elections" },
  mensa: { it: "Mensa", en: "Canteen" },
  organizzazione: { it: "Organizzazione", en: "General" },
};

/* ------------------------------------------------------------------ */
/* Stato                                                                */
/* ------------------------------------------------------------------ */
const store = {
  get(k, d) { try { const v = localStorage.getItem("elsa." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("elsa." + k, JSON.stringify(v)); } catch { /* privato */ } },
};
const state = {
  lang: store.get("lang", "it"),
  view: "new",
  data: null,
  seen: new Set(store.get("seen", [])),
  cat: "all",
  topic: null,
  showPast: false,
};
const uiLang = () => (state.lang === "en" ? "en" : "it");
const t = (k, ...a) => { const v = UI[uiLang()][k]; return typeof v === "function" ? v(...a) : v; };
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const locale = () => (state.lang === "en" ? "en-GB" : state.lang === "de" ? "de-DE" : "it-IT");

function applyStaticText() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll(".lang button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === state.lang)));
}

/* ------------------------------------------------------------------ */
/* Rete                                                                 */
/* ------------------------------------------------------------------ */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* vuoto */ }
  if (res.status === 401) { showLogin(); throw new Error("login"); }
  if (!res.ok) { const e = new Error((data && (data.detail || data.error)) || res.statusText); e.code = data && data.error; throw e; }
  return data;
}

/* ------------------------------------------------------------------ */
/* Date                                                                 */
/* ------------------------------------------------------------------ */
const today0 = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
const parseDay = (iso) => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };
const daysFromToday = (iso) => Math.round((parseDay(iso) - today0()) / 86400000);
function fmtDate(iso, withYear = false) {
  if (!iso) return "";
  return parseDay(iso).toLocaleDateString(locale(), { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });
}
function relDate(iso) {
  if (!iso) return "";
  const n = -daysFromToday(iso);
  if (n <= 0) return t("inDays", 0);
  if (n < 7) return t("daysAgo", n);
  return fmtDate(iso);
}

/* ------------------------------------------------------------------ */
/* Novità                                                               */
/* ------------------------------------------------------------------ */
function isNew(it) {
  if (it.category === "elternbriefe" || it.category === "umfragen") return it.new;
  if (state.seen.has(it.category + ":" + it.id)) return false;
  if (it.new) return true;
  // bacheca e messaggi: nuovi se recenti e mai aperti in quest'app
  return it.date ? -daysFromToday(it.date) <= 21 : false;
}
function markSeen(it) {
  state.seen.add(it.category + ":" + it.id);
  store.set("seen", [...state.seen].slice(-800));
}

const catOrder = ["elternbriefe", "umfragen", "klassenleitung", "fachlehrer", "schwarzes_brett"];
const byDateDesc = (a, b) => (b.date || "").localeCompare(a.date || "");

function itemHTML(it) {
  const cat = CATS[it.category] || { c: "var(--muted)" };
  const fresh = isNew(it);
  let tag = "";
  if (it.category === "elternbriefe" && it.can_confirm) tag = `<span class="tag need">${t("needs")}</span>`;
  else if (it.category === "umfragen" && it.new) tag = `<span class="tag need">${t("toVote")}</span>`;
  else if (fresh) tag = `<span class="tag">${t("newTag")}</span>`;
  const topic = TOPICS[it.topic] ? TOPICS[it.topic][uiLang()] : "";
  const when = it.category === "umfragen" && it.extra && it.extra.end
    ? `${t("pollEnds")} ${fmtDate(it.extra.end)}` : relDate(it.date);
  const snippet = it.body ? `<div class="item-snippet">${esc(it.body.replace(/\s+/g, " "))}</div>` : "";
  return `<button class="item ${fresh ? "is-new" : ""}" style="--c:${cat.c}" data-open="${esc(it.category)}:${esc(it.id)}">
    <div class="item-meta">${tag}<span>${esc(when)}</span>${it.sender ? `<span>${esc(it.sender)}</span>` : ""}<span>${esc(topic)}</span></div>
    <div class="item-title">${esc(it.title)}</div>${snippet}</button>`;
}

function groupHTML(cat, items) {
  const c = CATS[cat] || { it: cat, en: cat, c: "var(--muted)" };
  return `<section class="group"><h3 class="group-h" style="--c:${c.c}"><span class="dot"></span>${esc(c[uiLang()])}<span class="n">${items.length}</span></h3>
    ${items.map(itemHTML).join("")}</section>`;
}

function renderNew() {
  const items = state.data.items.filter(isNew);
  const count = items.length;
  const badge = $("#new-count");
  badge.hidden = count === 0; badge.textContent = count;
  if ("setAppBadge" in navigator) { try { count ? navigator.setAppBadge(count) : navigator.clearAppBadge(); } catch { /* */ } }

  if (!count) {
    $("#new-list").innerHTML = `<div class="empty"><span class="hand">${t("nothingNew")}</span>${t("nothingNewSub")}</div>`;
    return;
  }
  const groups = {};
  items.forEach((it) => (groups[it.category] ||= []).push(it));
  $("#new-list").innerHTML = catOrder.filter((c) => groups[c]).map((c) => groupHTML(c, groups[c].sort(byDateDesc))).join("");
}

function renderAll() {
  const present = catOrder.filter((c) => state.data.items.some((i) => i.category === c));
  $("#cat-filters").innerHTML = [["all", t("allCats")], ...present.map((c) => [c, CATS[c][uiLang()]])]
    .map(([k, label]) => `<button data-cat="${k}" aria-pressed="${state.cat === k}">${esc(label)}</button>`).join("");
  const inCat = state.data.items.filter((i) => state.cat === "all" || i.category === state.cat);
  const topics = [...new Set(inCat.map((i) => i.topic))].filter((x) => TOPICS[x]);
  $("#topic-filters").innerHTML = topics.length > 1 ? topics
    .map((k) => `<button data-topic="${k}" aria-pressed="${state.topic === k}">${esc(TOPICS[k][uiLang()])}</button>`).join("") : "";
  const list = inCat.filter((i) => !state.topic || i.topic === state.topic).sort(byDateDesc);
  if (state.cat === "all") {
    const groups = {};
    list.forEach((it) => (groups[it.category] ||= []).push(it));
    $("#all-list").innerHTML = catOrder.filter((c) => groups[c]).map((c) => groupHTML(c, groups[c])).join("") || `<div class="empty">—</div>`;
  } else {
    $("#all-list").innerHTML = `<section class="group">${list.map(itemHTML).join("")}</section>`;
  }
}

/* ------------------------------------------------------------------ */
/* Compiti in classe                                                    */
/* ------------------------------------------------------------------ */
function examLabel(e) { return e.subject ? e.title : e.title; }

function renderExamStrip() {
  const up = state.data.exams.filter((e) => daysFromToday(e.date) >= 0).slice(0, 10);
  if (!up.length) { $("#exam-strip").innerHTML = `<li class="exam-empty">${t("noExams")}</li>`; return; }
  $("#exam-strip").innerHTML = up.map((e) => {
    const d = parseDay(e.date); const n = daysFromToday(e.date);
    return `<li><button class="exam-chip ${e.kind === "test" ? "test" : ""} ${n <= 3 ? "soon" : ""}" data-goto="exams">
      <span class="day">${d.getDate()}</span>
      <span class="month">${esc(d.toLocaleDateString(locale(), { month: "short" }))}, ${esc(d.toLocaleDateString(locale(), { weekday: "short" }))}${e.time ? " " + esc(e.time) : ""}</span>
      <span class="subj">${esc(e.subject ? e.title.replace(/^(SA|Schulaufgabe|kLN|KA|Test)\s+(in|aus)\s+/i, "") || e.title : e.title)}</span>
      <span class="in">${esc(t("inDays", n))}</span></button></li>`;
  }).join("");
}

function renderExamCalendar() {
  const all = state.data.exams;
  const list = state.showPast ? all : all.filter((e) => daysFromToday(e.date) >= 0);
  if (!list.length) {
    $("#exam-calendar").innerHTML = `<div class="empty"><span class="hand">${t("noExams")}</span></div>${pastToggle(all)}`;
    return;
  }
  const months = {};
  list.forEach((e) => (months[e.date.slice(0, 7)] ||= []).push(e));
  $("#exam-calendar").innerHTML = Object.entries(months).map(([ym, es]) => {
    const name = parseDay(ym + "-01").toLocaleDateString(locale(), { month: "long", year: "numeric" });
    return `<section class="month-block"><h3>${esc(name)}</h3>${es.map((e) => {
      const d = parseDay(e.date); const n = daysFromToday(e.date);
      const orig = state.lang !== "de" && e.title_de !== e.title ? `<div class="s">${esc(e.title_de)}</div>` : "";
      return `<div class="exam-row ${e.kind === "test" ? "test" : ""} ${n < 0 ? "past" : ""}">
        <div class="d"><b>${d.getDate()}</b><span>${esc(d.toLocaleDateString(locale(), { weekday: "short" }))}</span></div>
        <div><div class="t">${esc(e.title)}</div>${orig}<div class="s">${e.time ? esc(e.time) + ", " : ""}${esc(n >= 0 ? t("inDays", n) : t("daysAgo", -n))}</div></div>
        <span class="kind ${e.kind === "test" ? "test" : ""}">${esc(t(e.kind))}</span></div>`;
    }).join("")}</section>`;
  }).join("") + pastToggle(all) + `<div class="cal-actions"><button class="btn" id="ics">${t("addCal")}</button></div>`;
}
function pastToggle(all) {
  if (!all.some((e) => daysFromToday(e.date) < 0)) return "";
  return `<div class="cal-actions"><button class="link" id="toggle-past">${state.showPast ? t("hidePast") : t("showPast")}</button></div>`;
}
function downloadICS() {
  const pad = (n) => String(n).padStart(2, "0");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Scuola di Elsa//IT", "CALSCALE:GREGORIAN", "X-WR-CALNAME:Compiti in classe Elsa"];
  state.data.exams.filter((e) => daysFromToday(e.date) >= 0).forEach((e) => {
    const d = parseDay(e.date); const ymd = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
    lines.push("BEGIN:VEVENT", `UID:${e.id}@scuola-di-elsa`, `SUMMARY:${(e.title + " (" + e.title_de + ")").replace(/[,;]/g, " ")}`);
    if (e.time) {
      const [h, m] = e.time.split(":").map(Number);
      lines.push(`DTSTART;TZID=Europe/Berlin:${ymd}T${pad(h)}${pad(m)}00`, `DURATION:PT90M`);
    } else {
      const n = new Date(d); n.setDate(n.getDate() + 1);
      lines.push(`DTSTART;VALUE=DATE:${ymd}`, `DTEND;VALUE=DATE:${n.getFullYear()}${pad(n.getMonth() + 1)}${pad(n.getDate())}`);
    }
    lines.push("BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:" + e.title.replace(/[,;]/g, " "), "END:VALARM", "END:VEVENT");
  });
  lines.push("END:VCALENDAR");
  const blob = new Blob([lines.join("\r\n")], { type: "text/calendar" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "compiti-in-classe-elsa.ics"; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

/* ------------------------------------------------------------------ */
/* Dettaglio                                                            */
/* ------------------------------------------------------------------ */
function openSheet(html) {
  $("#sheet-body").innerHTML = html;
  $("#sheet").hidden = false;
  document.body.style.overflow = "hidden";
  $(".sheet-close").focus();
}
function closeSheet() { $("#sheet").hidden = true; document.body.style.overflow = ""; }

function attachmentsHTML(list) {
  if (!list || !list.length) return "";
  return `<div class="attach"><strong>${t("attachments")}</strong>${list.map((a) =>
    `<a href="/api/file?u=${encodeURIComponent(a.href)}" target="_blank" rel="noopener">${esc(a.name)}</a>`).join("")}</div>`;
}

function openItem(key) {
  const it = state.data.items.find((i) => i.category + ":" + i.id === key);
  if (!it) return;
  if (it.category === "umfragen") return openPoll(it);
  const translated = state.lang !== "de" && (it.title_de !== it.title || it.body_de !== it.body);
  const meta = [relDate(it.date), it.sender ? `${t("from")}: ${it.sender}` : "", it.distribution ? `${t("classes")}: ${it.distribution}` : ""]
    .filter(Boolean).map(esc).join(", ");
  let actions = "";
  if (it.category === "elternbriefe") {
    actions = it.can_confirm
      ? `<button class="btn primary" data-confirm="${esc(it.id)}">${t("confirm")}</button>`
      : `<div class="done">✓ ${t("confirmed")}</div>`;
  } else if (isNew(it)) {
    actions = `<button class="btn" data-seen="${esc(key)}">${t("markRead")}</button>`;
  }
  openSheet(`
    <p class="item-meta">${meta}</p>
    <h2 id="sheet-title">${esc(it.title)}</h2>
    ${translated ? `<p class="orig-title">${esc(it.title_de)}</p>` : ""}
    <div class="body" id="body-text">${esc(it.body)}</div>
    ${translated ? `<button class="link" id="toggle-orig" data-state="tr">${t("showOriginal")}</button>` : ""}
    ${attachmentsHTML(it.attachments)}
    <div class="actions">${actions}</div>`);
  $("#toggle-orig")?.addEventListener("click", (ev) => {
    const b = ev.currentTarget; const showOrig = b.dataset.state === "tr";
    $("#body-text").textContent = showOrig ? it.body_de : it.body;
    b.dataset.state = showOrig ? "de" : "tr";
    b.textContent = showOrig ? t("hideOriginal") : t("showOriginal");
  });
  if (it.category !== "elternbriefe" && it.category !== "umfragen") { markSeen(it); renderNew(); }
}

async function confirmLetter(id, btn) {
  btn.disabled = true;
  try {
    await api(`/api/letters/${encodeURIComponent(id)}/confirm`, { method: "POST" });
    const it = state.data.items.find((i) => i.category === "elternbriefe" && i.id === id);
    if (it) { it.new = false; it.can_confirm = false; }
    btn.outerHTML = `<div class="done">✓ ${t("confirmed")}</div>`;
    toast(t("confirmed"));
    renderNew(); renderAll();
  } catch (e) { btn.disabled = false; toast(`${t("sendError")} ${e.message}`); }
}

/* ------------------------------------------------------------------ */
/* Sondaggi                                                             */
/* ------------------------------------------------------------------ */
async function openPoll(it) {
  openSheet(`<h2 id="sheet-title">${esc(it.title)}</h2><p class="muted">${t("loading")}</p>`);
  let p;
  try { p = await api(`/api/polls/${encodeURIComponent(it.id)}?lang=${state.lang}`); }
  catch (e) { $("#sheet-body").insertAdjacentHTML("beforeend", `<p class="error">${esc(e.message)}</p>`); return; }
  const showDe = state.lang !== "de";
  const fieldHTML = (f, i) => {
    const q = `${esc(f.question)}${showDe && f.question_de && f.question_de !== f.question ? `<small class="muted"> (${esc(f.question_de)})</small>` : ""}`;
    const dis = p.locked || f.disabled ? "disabled" : "";
    if (f.type === "radio" || f.type === "checkbox") {
      return `<div class="poll-field"><fieldset><legend>${q}</legend>${f.options.map((o, j) => `
        <label class="opt"><input type="${f.type}" name="f${i}" data-name="${esc(f.name)}" value="${esc(o.value)}" ${o.checked ? "checked" : ""} ${dis}>
        <span>${esc(o.label)}${showDe && o.label_de !== o.label ? `<small>${esc(o.label_de)}</small>` : ""}</span></label>`).join("")}</fieldset></div>`;
    }
    if (f.type === "select") {
      return `<div class="poll-field"><label class="q" for="f${i}">${q}</label><select id="f${i}" data-name="${esc(f.name)}" ${dis}>${f.options.map((o) =>
        `<option value="${esc(o.value)}" ${o.checked ? "selected" : ""}>${esc(o.label)}</option>`).join("")}</select></div>`;
    }
    const tag = f.type === "textarea" ? `<textarea id="f${i}" rows="3" data-name="${esc(f.name)}" ${dis}>${esc(f.value)}</textarea>`
      : `<input type="text" id="f${i}" data-name="${esc(f.name)}" value="${esc(f.value)}" ${dis}>`;
    return `<div class="poll-field"><label class="q" for="f${i}">${q}</label>${tag}</div>`;
  };
  const status = p.voted ? `<div class="done">✓ ${t("alreadyVoted")} ${esc(fmtDate(p.voted, true))}</div>`
    : p.locked ? `<p class="muted">${t("pollClosed")}</p>` : "";
  $("#sheet-body").innerHTML = `
    <p class="item-meta">${p.end ? esc(`${t("pollEnds")} ${fmtDate(p.end, true)}`) : ""}</p>
    <h2 id="sheet-title">${esc(p.title)}</h2>
    ${showDe && p.title_de !== p.title ? `<p class="orig-title">${esc(p.title_de)}</p>` : ""}
    <div class="body" id="body-text">${esc(p.description)}</div>
    ${showDe && p.description_de && p.description_de !== p.description ? `<button class="link" id="toggle-orig" data-state="tr">${t("showOriginal")}</button>` : ""}
    ${attachmentsHTML(p.attachments)}
    <form id="poll-form">${p.fields.map(fieldHTML).join("")}
      <div id="poll-confirm"></div>
      <div class="actions">${status || `<button class="btn primary" type="submit">${t("sendVote")}</button>`}</div>
    </form>`;
  $("#toggle-orig")?.addEventListener("click", (ev) => {
    const b = ev.currentTarget; const showOrig = b.dataset.state === "tr";
    $("#body-text").textContent = showOrig ? p.description_de : p.description;
    b.dataset.state = showOrig ? "de" : "tr"; b.textContent = showOrig ? t("hideOriginal") : t("showOriginal");
  });
  $("#poll-form").addEventListener("submit", (ev) => { ev.preventDefault(); askPollConfirm(it, p); });
}

function collectAnswers(p) {
  const answers = {};
  p.fields.forEach((f, i) => {
    if (f.type === "radio") { const c = $(`input[name="f${i}"]:checked`); if (c) answers[f.name] = c.value; }
    else if (f.type === "checkbox") { const cs = [...document.querySelectorAll(`input[name="f${i}"]:checked`)].map((c) => c.value); if (cs.length) answers[f.name] = cs; }
    else { const el = $(`#f${i}`); if (el && el.value.trim()) answers[f.name] = el.value; }
  });
  return answers;
}

function askPollConfirm(it, p) {
  const answers = collectAnswers(p);
  if (!Object.keys(answers).length) { toast(t("pickAnswer")); return; }
  $("#poll-confirm").innerHTML = `<div class="confirm-box"><p>${t("confirmSend")}</p>
    <div class="actions"><button type="button" class="btn danger" id="do-send">${t("yesSend")}</button>
    <button type="button" class="btn" id="no-send">${t("cancel")}</button></div></div>`;
  $("#no-send").onclick = () => { $("#poll-confirm").innerHTML = ""; };
  $("#do-send").onclick = async (ev) => {
    ev.currentTarget.disabled = true;
    try {
      await api(`/api/polls/${encodeURIComponent(it.id)}`, { method: "POST", body: { answers } });
      it.new = false; it.extra.voted = new Date().toISOString().slice(0, 10);
      toast(t("voted")); closeSheet(); renderNew(); renderAll();
      load(true, true);
    } catch (e) { ev.currentTarget.disabled = false; toast(`${t("sendError")} ${e.message}`); }
  };
}

/* ------------------------------------------------------------------ */
/* Caricamento                                                          */
/* ------------------------------------------------------------------ */
let toastTimer;
function toast(msg) {
  const el = $("#toast"); el.textContent = msg; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (el.hidden = true), 3200);
}

function renderAllViews() {
  const d = state.data;
  $("#who").textContent = d.student || "";
  $("#who").title = d.school || "";
  $("#updated").textContent = `${t("updated")} ${new Date(d.updated * 1000).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" })}`;
  const banner = $("#banner");
  if (d.errors && d.errors.length) { banner.hidden = false; banner.textContent = `${t("partial")} ${d.errors.join("; ")}`; }
  else banner.hidden = true;
  renderExamStrip(); renderNew(); renderAll(); renderExamCalendar();
}

async function load(force = false, quiet = false) {
  const btn = $("#refresh"); btn.classList.add("spin");
  if (!state.data && !quiet) $("#new-list").innerHTML = `<div class="empty">${t("loading")}</div>`;
  try {
    state.data = await api(`/api/overview?lang=${state.lang}${force ? "&refresh=1" : ""}`);
    store.set("lastData", state.data);
    renderAllViews();
  } catch (e) {
    if (e.message === "login") return;
    const msg = e.code === "portal_login" ? t("errPortalLogin") : t("errNetwork");
    const cached = store.get("lastData", null);
    if (!state.data && cached && cached.lang === state.lang) { state.data = cached; renderAllViews(); }
    const banner = $("#banner"); banner.hidden = false; banner.textContent = msg;
  } finally { btn.classList.remove("spin"); }
}

function setView(v) {
  state.view = v;
  ["new", "all", "exams"].forEach((k) => ($(`#view-${k}`).hidden = k !== v));
  $("#exam-strip-wrap").hidden = v === "exams";
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  window.scrollTo({ top: 0 });
}

function showLogin() { $("#main").hidden = true; $("#login").hidden = false; applyStaticText(); $("#pin").focus(); }
function showMain() { $("#login").hidden = true; $("#main").hidden = false; applyStaticText(); load(); }

/* ------------------------------------------------------------------ */
/* Eventi                                                               */
/* ------------------------------------------------------------------ */
document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-open],[data-goto],[data-view],[data-close],[data-confirm],[data-seen],[data-cat],[data-topic],[data-lang],#toggle-past,#ics");
  if (!el) return;
  if (el.dataset.open) openItem(el.dataset.open);
  else if (el.dataset.goto) setView(el.dataset.goto);
  else if (el.dataset.view) setView(el.dataset.view);
  else if (el.hasAttribute("data-close")) closeSheet();
  else if (el.dataset.confirm) confirmLetter(el.dataset.confirm, el);
  else if (el.dataset.seen) {
    const it = state.data.items.find((i) => i.category + ":" + i.id === el.dataset.seen);
    if (it) { markSeen(it); el.outerHTML = `<div class="done">✓ ${t("markedRead")}</div>`; renderNew(); renderAll(); }
  } else if (el.dataset.cat) { state.cat = el.dataset.cat; state.topic = null; renderAll(); }
  else if (el.dataset.topic) { state.topic = state.topic === el.dataset.topic ? null : el.dataset.topic; renderAll(); }
  else if (el.dataset.lang) {
    state.lang = el.dataset.lang; store.set("lang", state.lang); applyStaticText();
    if (state.data) renderAllViews();
    load(false, true);
  } else if (el.id === "toggle-past") { state.showPast = !state.showPast; renderExamCalendar(); }
  else if (el.id === "ics") downloadICS();
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !$("#sheet").hidden) closeSheet(); });
$("#refresh").addEventListener("click", () => load(true));
$("#login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("#login-error").textContent = "";
  try {
    await api("/api/login", { method: "POST", body: { pin: $("#pin").value } });
    $("#pin").value = ""; showMain();
  } catch (e) { $("#login-error").textContent = e.code === "too_many" ? t("tooMany") : t("wrongPin"); }
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && state.data && Date.now() / 1000 - state.data.updated > 600) load(false, true);
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

(async () => {
  applyStaticText();
  try { const me = await (await fetch("/api/me", { credentials: "same-origin" })).json(); me.authed ? showMain() : showLogin(); }
  catch { showLogin(); }
})();
