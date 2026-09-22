const RATINGS = ["interesting", "neutral", "not_interested"];
const LABEL = {
  interesting: "Interessant",
  neutral: "Neutraal",
  not_interested: "Niet interessant",
};
const DOT = {
  interesting: "🟢",
  neutral: "⚪",
  not_interested: "🔴",
};

let topics = [];

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function fmtDay(day) {
  const [y, m, d] = day.split("-");
  const names = ["januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december"];
  return `${parseInt(d)} ${names[parseInt(m) - 1]} ${y}`;
}

function groupByDay(items) {
  const map = {};
  items.forEach(t => (map[t.day] ||= []).push(t));
  return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function topicCard(t) {
  const card = document.createElement("div");
  card.className = "topic";
  card.innerHTML = `
    <div class="t-title">${escapeHtml(t.title)}</div>
    ${t.category ? `<div class="t-cat">${escapeHtml(t.category)}</div>` : ""}
    ${t.description ? `<div class="t-desc">${escapeHtml(t.description)}</div>` : ""}
    ${t.url ? `<a class="t-url" href="${escapeHtml(t.url)}" target="_blank" rel="noopener">bron ↗</a>` : ""}
    <div class="t-rate"></div>`;

  const box = card.querySelector(".t-rate");
  RATINGS.forEach(r => {
    const b = document.createElement("button");
    b.className = "rate " + r;
    b.textContent = (t.rating === r ? "● " : "○ ") + LABEL[r];
    if (t.rating === r) b.classList.add("active");
    b.addEventListener("click", () => saveRating(t.id, r));
    box.appendChild(b);
  });
  return card;
}

async function saveRating(id, rating) {
  try {
    await api(`/api/topics/${id}/rating`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    });
    const t = topics.find(x => x.id === id);
    if (t) t.rating = rating;
    render();
  } catch (e) {
    console.error("save failed", e);
  }
}

function render() {
  const main = document.getElementById("days");
  main.innerHTML = "";

  const groups = groupByDay(topics);
  document.getElementById("cnt-d").textContent = groups.length;

  groups.forEach(([day, items]) => {
    const counts = { interesting: 0, neutral: 0, not_interested: 0 };
    items.forEach(t => counts[t.rating]++);

    const sec = document.createElement("section");
    sec.className = "day";
    sec.innerHTML = `<h2 class="d-head">${fmtDay(day)} <span class="d-count">${items.length} onderwerpen</span></h2>
      <div class="d-dots"><span>🟢 ${counts.interesting}</span><span>⚪ ${counts.neutral}</span><span>🔴 ${counts.not_interested}</span></div>`;
    items.forEach(t => sec.appendChild(topicCard(t)));
    main.appendChild(sec);
  });

  const o = { interesting: 0, neutral: 0, not_interested: 0 };
  topics.forEach(t => o[t.rating]++);
  document.getElementById("cnt-i").textContent = o.interesting;
  document.getElementById("cnt-n").textContent = o.neutral;
  document.getElementById("cnt-x").textContent = o.not_interested;
  document.getElementById("profile").hidden = false;
}

async function main() {
  const data = await api("/api/topics");
  topics = data.topics;
  render();
}

main().catch(e => {
  document.getElementById("days").innerHTML =
    `<p class="err">Kan data niet laden: ${escapeHtml(String(e))}</p>`;
});