<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Trading AI</title>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; }

body {
  font-family: 'Open Sans', sans-serif;
  background: #0f172a;
  color: white;
  text-align: center;
  padding: 20px;
  margin: 0;
}

.container {
  max-width: 550px;
  margin: auto;
  background: #1e293b;
  padding: 24px;
  border-radius: 12px;
}

input, button, select {
  width: 100%;
  padding: 10px;
  margin: 6px 0;
  border-radius: 6px;
  border: none;
  font-family: inherit;
  font-size: 0.95em;
}

input {
  background: #0f172a;
  color: white;
}

input::placeholder { color: #475569; }

select {
  background: #0f172a;
  color: white;
  cursor: pointer;
}

select option { background: #1e293b; }

.row-2 { display: flex; gap: 10px; }
.row-2 input, .row-2 select { width: 50%; margin: 6px 0; }

button {
  background: #38bdf8;
  font-weight: bold;
  cursor: pointer;
  color: #0f172a;
  transition: background 0.2s;
}

button:hover { background: #7dd3fc; }

.btn-secondary {
  background: #334155;
  color: white;
}

.btn-secondary:hover { background: #475569; }

#dropHTF, #dropLTF {
  border: 2px dashed #38bdf8;
  padding: 20px;
  margin: 8px 0;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
  font-size: 0.9em;
}

#dropHTF:hover, #dropLTF:hover { background: #0f172a55; }

#loader { display: none; margin: 10px; }

#result {
  background: #020617;
  padding: 14px;
  border-radius: 6px;
  text-align: left;
  margin-top: 10px;
  line-height: 1.7;
}

.result-section {
  margin-bottom: 10px;
  border-left: 3px solid #38bdf8;
  padding-left: 10px;
}

.result-label {
  color: #38bdf8;
  font-size: 0.75em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}

.result-badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 0.9em;
}

.badge-buy  { background: #16a34a; color: white; }
.badge-sell { background: #dc2626; color: white; }
.badge-neutre { background: #ca8a04; color: white; }

hr { border: none; border-top: 1px solid #334155; margin: 14px 0; }

.tip {
  font-size: 0.75em;
  color: #64748b;
  margin: 2px 0 8px 0;
  text-align: left;
}

/* ── Barre quota ── */
#quotaBar {
  background: #020617;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85em;
}

.quota-track {
  flex: 1;
  height: 6px;
  background: #334155;
  border-radius: 3px;
  margin: 0 12px;
  overflow: hidden;
}

.quota-fill {
  height: 100%;
  border-radius: 3px;
  background: #38bdf8;
  transition: width 0.4s;
}

/* ── Écran Auth ── */
#authScreen {
  background: #020617;
  padding: 20px;
  border-radius: 10px;
}

#authScreen h3 { margin-top: 0; color: #38bdf8; }

.auth-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.auth-tab {
  flex: 1;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  background: #1e293b;
  color: #94a3b8;
  font-weight: bold;
  border: none;
  transition: all 0.2s;
}

.auth-tab.active {
  background: #38bdf8;
  color: #0f172a;
}

#authMessage { font-size: 0.85em; margin-top: 8px; min-height: 20px; }

/* ── Header utilisateur ── */
#userHeader {
  display: none;
  background: #020617;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
  display: none;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85em;
}

#userHeader.visible {
  display: flex;
}

.plan-badge {
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.8em;
  font-weight: bold;
}

.plan-free    { background: #334155; color: #94a3b8; }
.plan-premium { background: #0369a1; color: white; }
.plan-pro     { background: #7c3aed; color: white; }

/* ── Modal upgrade ── */
#upgradeModal {
  display: none;
  position: fixed;
  inset: 0;
  background: #000000cc;
  z-index: 100;
  align-items: center;
  justify-content: center;
}

#upgradeModal.visible { display: flex; }

.modal-box {
  background: #1e293b;
  border-radius: 14px;
  padding: 28px;
  max-width: 480px;
  width: 90%;
  text-align: center;
}

.modal-box h2 { color: #38bdf8; margin-top: 0; }

.plans {
  display: flex;
  gap: 14px;
  margin: 20px 0;
}

.plan-card {
  flex: 1;
  background: #020617;
  border-radius: 10px;
  padding: 18px 12px;
  border: 2px solid #334155;
  transition: border 0.2s;
}

.plan-card:hover { border-color: #38bdf8; }

.plan-card.popular { border-color: #7c3aed; }

.plan-card .price {
  font-size: 1.6em;
  font-weight: bold;
  color: white;
}

.plan-card .price span {
  font-size: 0.5em;
  color: #94a3b8;
}

.plan-card ul {
  list-style: none;
  padding: 0;
  margin: 12px 0;
  font-size: 0.85em;
  color: #94a3b8;
  text-align: left;
}

.plan-card ul li::before { content: "✓ "; color: #38bdf8; }

.btn-premium {
  background: #0369a1;
  color: white;
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-premium:hover { background: #0284c7; }

.btn-pro {
  background: #7c3aed;
  color: white;
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-pro:hover { background: #6d28d9; }

.modal-close {
  background: none;
  border: none;
  color: #64748b;
  font-size: 0.85em;
  cursor: pointer;
  margin-top: 4px;
  width: auto;
  padding: 6px;
}

.modal-close:hover { color: white; background: none; }

/* ── Pastille probabilité ── */
.proba-pastille {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1em;
  font-weight: bold;
}
.proba-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.hidden { display: none; }
</style>
</head>
<body>

<!-- ── Modal Upgrade ── -->
<div id="upgradeModal">
  <div class="modal-box">
    <h2>🚀 Passez à la version supérieure</h2>
    <p style="color:#94a3b8;">Vous avez atteint votre limite. Choisissez un plan pour continuer.</p>

    <div class="plans">
      <div class="plan-card">
        <div style="font-weight:bold; margin-bottom:6px;">Premium</div>
        <div class="price">19€<span>/mois</span></div>
        <ul>
          <li>50 analyses/mois</li>
          <li>GPT-4o Vision</li>
          <li>Analyse SMC</li>
          <li>Multi-timeframe</li>
        </ul>
        <button class="btn-premium" onclick="subscribe('premium')">Choisir Premium</button>
      </div>

      <div class="plan-card popular">
        <div style="font-weight:bold; margin-bottom:6px; color:#a78bfa;">⭐ Pro</div>
        <div class="price">39€<span>/mois</span></div>
        <ul>
          <li>Analyses illimitées</li>
          <li>GPT-4o Vision</li>
          <li>Analyse SMC</li>
          <li>Multi-timeframe</li>
        </ul>
        <button class="btn-pro" onclick="subscribe('pro')">Choisir Pro</button>
      </div>
    </div>

    <button class="modal-close" onclick="closeModal()">✕ Fermer</button>
  </div>
</div>

<!-- ── App principale ── -->
<div class="container">
  <h2>Analyse Graphique IA 🧠</h2>

  <!-- Header utilisateur connecté -->
  <div id="userHeader">
    <span id="userEmail" style="color:#94a3b8;"></span>
    <span id="userPlanBadge" class="plan-badge plan-free">FREE</span>
    <button onclick="logout()" style="width:auto; padding:4px 12px; font-size:0.8em; background:#334155; color:white;">Déconnexion</button>
  </div>

  <!-- Barre quota -->
  <div id="quotaBar" class="hidden">
    <span id="quotaLabel" style="white-space:nowrap;">0 analyses</span>
    <div class="quota-track">
      <div class="quota-fill" id="quotaFill" style="width:0%"></div>
    </div>
    <span id="quotaMax" style="white-space:nowrap; color:#64748b;"></span>
  </div>

  <!-- Écran Auth (affiché si non connecté) -->
  <div id="authScreen">
    <h3>Connecte-toi pour analyser</h3>
    <div class="auth-tabs">
      <button class="auth-tab active" id="tabLogin" onclick="switchTab('login')">Se connecter</button>
      <button class="auth-tab" id="tabRegister" onclick="switchTab('register')">S'inscrire</button>
    </div>
    <input type="email" id="authEmail" placeholder="Email">
    <input type="password" id="authPassword" placeholder="Mot de passe">
    <button id="authBtn" onclick="doAuth()">Se connecter</button>
    <p id="authMessage"></p>
  </div>

  <!-- App (masquée si non connecté) -->
  <div id="appContent" class="hidden">

    <div class="row-2">
      <input type="text" id="asset" placeholder="Actif (ex: EURUSD, BTC...)">
      <select id="timeframe">
        <option value="">Timeframe</option>
        <option value="M1">M1</option>
        <option value="M5">M5</option>
        <option value="M15">M15</option>
        <option value="H1">H1</option>
        <option value="H4">H4</option>
        <option value="D1">D1</option>
        <option value="W1">W1</option>
      </select>
    </div>

    <p class="tip">💡 Screenshot plein écran, fond uniforme, 50+ bougies visibles</p>

    <div id="dropHTF">📈 Image High TimeFrame (M15 · H1 · H4)</div>
    <input type="file" id="imageHTF" accept="image/*" class="hidden">

    <div id="dropLTF">📉 Image Low TimeFrame (M1 · M5 · M15) — optionnelle</div>
    <input type="file" id="imageLTF" accept="image/*" class="hidden">

    <button onclick="analyze()">Analyser</button>
    <button onclick="resetForm()" class="btn-secondary" style="margin-top:4px;">Reset</button>
    <button onclick="document.getElementById('upgradeModal').classList.add('visible')" style="margin-top:4px; background: linear-gradient(135deg, #0369a1, #7c3aed); color:white;">⭐ Voir les offres Premium & Pro</button>

    <div id="loader">⏳ Analyse en cours...</div>
    <div id="result"></div>
  </div>
</div>

<script>
const API = "https://trading-ai-7y8g.onrender.com";
let currentUser = null;
let authMode = "login";

// ── Auth tabs ─────────────────────────────────────────────────────────────────
function switchTab(mode) {
  authMode = mode;
  document.getElementById("tabLogin").classList.toggle("active", mode === "login");
  document.getElementById("tabRegister").classList.toggle("active", mode === "register");
  document.getElementById("authBtn").textContent = mode === "login" ? "Se connecter" : "S'inscrire";
  document.getElementById("authMessage").textContent = "";
}

async function doAuth() {
  const email    = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const msg      = document.getElementById("authMessage");

  if (!email || !password) { msg.textContent = "Remplis tous les champs"; return; }

  const endpoint = authMode === "login" ? "/login" : "/register";

  try {
    const res  = await fetch(API + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.error) { msg.textContent = "❌ " + data.error; return; }

    // Si inscription → auto-login
    if (authMode === "register") {
      msg.textContent = "✅ Inscription réussie ! Connexion...";
      authMode = "login";
      setTimeout(() => doAuth(), 800);
      return;
    }

    // Connexion réussie
    currentUser = { ...data.user, password };
    localStorage.setItem("tradingUser", JSON.stringify(currentUser));
    showApp();

  } catch (e) {
    msg.textContent = "Erreur réseau";
  }
}

// ── Session ───────────────────────────────────────────────────────────────────
function loadSession() {
  const saved = localStorage.getItem("tradingUser");
  if (saved) {
    currentUser = JSON.parse(saved);
    showApp();
  }
}

function showApp() {
  document.getElementById("authScreen").classList.add("hidden");
  document.getElementById("appContent").classList.remove("hidden");
  document.getElementById("userHeader").classList.add("visible");
  document.getElementById("userEmail").textContent = currentUser.email;

  const planLabel = { free: "FREE", premium: "PREMIUM", pro: "PRO" };
  const planClass = { free: "plan-free", premium: "plan-premium", pro: "plan-pro" };
  const badge = document.getElementById("userPlanBadge");
  badge.textContent = planLabel[currentUser.plan] || "FREE";
  badge.className = "plan-badge " + (planClass[currentUser.plan] || "plan-free");

  updateQuota();
}

function logout() {
  localStorage.removeItem("tradingUser");
  currentUser = null;
  document.getElementById("authScreen").classList.remove("hidden");
  document.getElementById("appContent").classList.add("hidden");
  document.getElementById("userHeader").classList.remove("visible");
  document.getElementById("result").innerHTML = "";
  document.getElementById("quotaBar").classList.add("hidden");
}

function updateQuota() {
  if (!currentUser) return;

  const plan  = currentUser.plan;
  const used  = currentUser.analyses_utilisees || 0;
  const bar   = document.getElementById("quotaBar");
  const fill  = document.getElementById("quotaFill");
  const label = document.getElementById("quotaLabel");
  const max   = document.getElementById("quotaMax");

  bar.classList.remove("hidden");

  if (plan === "pro") {
    label.textContent = `${used} analyses`;
    fill.style.width  = "30%";
    fill.style.background = "#7c3aed";
    max.textContent   = "Illimité ∞";
  } else {
    const limit = plan === "premium" ? 50 : 2;
    const pct   = Math.min(100, (used / limit) * 100);
    label.textContent = `${used}/${limit} analyses`;
    fill.style.width  = pct + "%";
    fill.style.background = pct >= 90 ? "#dc2626" : pct >= 60 ? "#ca8a04" : "#38bdf8";
    max.textContent   = plan === "premium" ? "Premium" : "Free";
  }
}

// ── Stripe ────────────────────────────────────────────────────────────────────
async function subscribe(plan) {
  if (!currentUser) return;

  try {
    const res  = await fetch(API + "/create-checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: currentUser.email, plan })
    });
    const data = await res.json();
    if (data.url) window.location.href = data.url;
    else alert("Erreur : " + data.error);
  } catch (e) {
    alert("Erreur réseau");
  }
}

function closeModal() {
  document.getElementById("upgradeModal").classList.remove("visible");
}

// ── Retour après paiement ─────────────────────────────────────────────────────
function checkPaymentReturn() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("payment") === "success") {
    const plan = params.get("plan");
    if (currentUser) {
      currentUser.plan = plan;
      currentUser.analyses_utilisees = 0;
      localStorage.setItem("tradingUser", JSON.stringify(currentUser));
      showApp();
      closeModal();
      alert(`🎉 Abonnement ${plan} activé ! Bienvenue.`);
    }
    window.history.replaceState({}, "", window.location.pathname);
  }
}

// ── Drag & drop ───────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadSession();
  checkPaymentReturn();

  const dropHTF  = document.getElementById("dropHTF");
  const dropLTF  = document.getElementById("dropLTF");
  const imageHTF = document.getElementById("imageHTF");
  const imageLTF = document.getElementById("imageLTF");

  dropHTF.onclick = () => imageHTF.click();
  dropHTF.ondragover = e => e.preventDefault();
  dropHTF.ondrop = e => { e.preventDefault(); imageHTF.files = e.dataTransfer.files; dropHTF.textContent = "✅ HTF chargée"; };

  dropLTF.onclick = () => imageLTF.click();
  dropLTF.ondragover = e => e.preventDefault();
  dropLTF.ondrop = e => { e.preventDefault(); imageLTF.files = e.dataTransfer.files; dropLTF.textContent = "✅ LTF chargée"; };

  imageHTF.onchange = () => { if (imageHTF.files.length) dropHTF.textContent = "✅ HTF chargée"; };
  imageLTF.onchange = () => { if (imageLTF.files.length) dropLTF.textContent = "✅ LTF chargée"; };
});

function resetForm() {
  document.getElementById("imageHTF").value = "";
  document.getElementById("imageLTF").value = "";
  document.getElementById("result").innerHTML = "";
  document.getElementById("asset").value = "";
  document.getElementById("timeframe").value = "";
  document.getElementById("dropHTF").textContent = "📈 Image High TimeFrame (M15 · H1 · H4)";
  document.getElementById("dropLTF").textContent = "📉 Image Low TimeFrame (M1 · M5 · M15) — optionnelle";
}

// ── Analyse ───────────────────────────────────────────────────────────────────
async function analyze() {
  if (!currentUser) { alert("Connecte-toi d'abord"); return; }

  const imageHTF = document.getElementById("imageHTF");
  const imageLTF = document.getElementById("imageLTF");
  const loader   = document.getElementById("loader");
  const result   = document.getElementById("result");

  if (!imageHTF.files.length && !imageLTF.files.length) {
    alert("Ajoute au moins une image");
    return;
  }

  loader.style.display = "block";
  result.innerHTML = "";

  const formData = new FormData();
  formData.append("email",    currentUser.email);
  formData.append("password", currentUser.password);

  const asset     = document.getElementById("asset").value;
  const timeframe = document.getElementById("timeframe").value;
  if (asset)     formData.append("asset", asset);
  if (timeframe) formData.append("timeframe", timeframe);

  if (imageHTF.files.length) formData.append("image_htf", imageHTF.files[0]);
  if (imageLTF.files.length) formData.append("image_ltf", imageLTF.files[0]);

  try {
    const response = await fetch(API + "/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.error === "LIMIT_REACHED") {
      document.getElementById("upgradeModal").classList.add("visible");
      return;
    }

    if (data.error) {
      result.textContent = "Erreur : " + data.error;
      return;
    }

    // Met à jour le compteur local
    currentUser.analyses_utilisees = (currentUser.analyses_utilisees || 0) + 1;
    localStorage.setItem("tradingUser", JSON.stringify(currentUser));
    updateQuota();

    renderResult(data);

  } catch (err) {
    result.textContent = "Erreur réseau : " + err.message;
  } finally {
    loader.style.display = "none";
  }
}

function probaHtml(score) {
  const color = score >= 70 ? '#22c55e' : score >= 55 ? '#facc15' : '#f87171';
  const label = score >= 70 ? 'Bon setup' : score >= 55 ? 'Setup moyen' : 'Setup faible';
  return `
    <div class="result-section">
      <div class="result-label">Probabilité de succès</div>
      <div class="proba-pastille">
        <span class="proba-dot" style="background:` + color + `"></span>
        <span style="color:` + color + `">` + score + `% — ` + label + `</span>
      </div>
    </div>`;
}

function renderResult(data) {
  const result   = document.getElementById("result");
  const dirClass = data.direction === "BUY" ? "badge-buy" : data.direction === "SELL" ? "badge-sell" : "badge-neutre";

  const confluences = Array.isArray(data.confluences) && data.confluences.length
    ? data.confluences.map(c => `• ${c}`).join("<br>")
    : "—";

  const entrees = Array.isArray(data.entrees) ? data.entrees.join(" / ") : data.entrees;
  const tps     = Array.isArray(data.take_profit) ? data.take_profit.join(" · ") : data.take_profit;

  result.innerHTML = `
    <div class="result-section">
      <div class="result-label">Direction</div>
      <span class="result-badge ${dirClass}">${data.direction}</span>
      ${data.ratio_risque_rendement ? `<span style="margin-left:8px;color:#94a3b8;font-size:0.85em;">R/R ${data.ratio_risque_rendement}</span>` : ""}
    </div>
    <div class="result-section">
      <div class="result-label">Zone(s) d'entrée</div>
      ${entrees}
    </div>
    <div class="result-section">
      <div class="result-label">Stop Loss</div>
      ${data.stop_loss}
    </div>
    <div class="result-section">
      <div class="result-label">Take Profit</div>
      ${tps}
    </div>
    ${data.confluences ? `
    <div class="result-section">
      <div class="result-label">Confluences</div>
      ${confluences}
    </div>` : ""}
    ${data.invalidation ? `
    <div class="result-section">
      <div class="result-label">Invalidation</div>
      <span style="color:#f87171;">${data.invalidation}</span>
    </div>` : ""}
    ${data.probabilite_succes !== undefined ? probaHtml(data.probabilite_succes) : ""}
    <hr>
    <div class="result-section">
      <div class="result-label">Analyse</div>
      ${data.explication}
    </div>
  `;
}
</script>
</body>
</html>























