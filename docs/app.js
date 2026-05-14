/* =====================================================================
   Computer \u00b7 AR Display
   ---------------------------------------------------------------------
   Webcam \u2192 MediaPipe Hands (21 Landmark-Punkte pro Hand) \u2192 Canvas-Overlay
   mit schwebenden App-Icons. Pinch-Geste (Daumen+Zeigefinger nah) zum
   Greifen, Index-Hover mit Hold zum Aktivieren. WebSocket-Verbindung
   zum Python-Assistenten pusht Icons rein und schickt Klicks zur\u00fcck.
   ===================================================================== */

'use strict';

// ---------- DOM ------------------------------------------------------------
const video      = document.getElementById('webcam');
const canvas     = document.getElementById('overlay');
const ctx        = canvas.getContext('2d');
const startPanel = document.getElementById('start');
const startBtn   = document.getElementById('start-btn');
const wsDot      = document.getElementById('ws-dot');
const wsStatus   = document.getElementById('ws-status');
const handStatus = document.getElementById('hand-status');
const iconCount  = document.getElementById('icon-count');
const fpsEl      = document.getElementById('fps');
const gestureEl  = document.getElementById('gesture-status');
const subtitle   = document.getElementById('subtitle');
const demoBadge  = document.getElementById('demo-badge');

// ---------- Globaler State ------------------------------------------------
const state = {
  icons: [],          // { id, app, label, x, y, color, heldBy, hoveredSince, activating }
  hands: [],          // Aktuelle Hand-Landmarks (normalisiert 0..1)
  trail: [],          // Finger-Spur f\u00fcr visuellen Effekt
  lastFrameTime: 0,
  fps: 0,
  ws: null,
  particles: [],      // Partikel-Effekte bei Aktivierung
};

// Bekannte App-Icons \u2013 Emoji als schnelles visuelles Kennzeichen.
// Einfach, klar lesbar, keine externen Assets n\u00f6tig.
const APP_CATALOG = {
  spotify: { emoji: '\ud83c\udfb5', color: '#1db954', label: 'Spotify' },
  youtube: { emoji: '\u25b6',       color: '#ff0000', label: 'YouTube' },
  github:  { emoji: '\u23fd',       color: '#ffffff', label: 'GitHub' },
  discord: { emoji: '\ud83d\udcac', color: '#5865f2', label: 'Discord' },
  netflix: { emoji: 'N',           color: '#e50914', label: 'Netflix' },
  twitch:  { emoji: '\ud83c\udfae', color: '#9146ff', label: 'Twitch' },
  gmail:   { emoji: '\u2709',       color: '#ea4335', label: 'Gmail' },
  maps:    { emoji: '\ud83d\uddfa', color: '#4285f4', label: 'Maps' },
  chatgpt: { emoji: '\ud83e\udd16', color: '#10a37f', label: 'ChatGPT' },
  claude:  { emoji: '\u25c7',       color: '#d4a373', label: 'Claude' },
};

function appMeta(app) {
  return APP_CATALOG[app] || { emoji: '\u25a0', color: '#00ffe1', label: app };
}

// ---------- Canvas-Gr\u00f6\u00dfe ----------------------------------------------
function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

// ---------- WebSocket zum Python-Assistenten -----------------------------
// Mehrere Versuche; wenn es fehlschl\u00e4gt laufen wir im Demo-Modus weiter.
function connectWS() {
  const url = 'ws://localhost:8765';
  try {
    const ws = new WebSocket(url);
    state.ws = ws;

    ws.onopen = () => {
      wsDot.className = 'dot dot--on';
      wsStatus.textContent = 'LINKED';
      demoBadge.classList.remove('visible');
      ws.send(JSON.stringify({ type: 'hello' }));
    };

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      handleServerMessage(msg);
    };

    ws.onclose = () => {
      wsDot.className = 'dot dot--off';
      wsStatus.textContent = 'OFFLINE';
      demoBadge.classList.add('visible');
      // Reconnect-Versuch in 3s
      setTimeout(connectWS, 3000);
    };

    ws.onerror = () => { /* onclose kommt direkt danach */ };
  } catch (e) {
    wsDot.className = 'dot dot--off';
    wsStatus.textContent = 'OFFLINE';
    demoBadge.classList.add('visible');
    setTimeout(connectWS, 3000);
  }
}

function handleServerMessage(msg) {
  switch (msg.type) {
    case 'add_icon':
      addIcon(msg.app, msg.label);
      break;
    case 'remove_icon':
      removeIcon(msg.app);
      break;
    case 'clear_icons':
      state.icons = [];
      updateIconCount();
      break;
    case 'speak':
      showSubtitle(msg.text);
      break;
  }
}

function sendClick(app) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: 'icon_clicked', app }));
  } else {
    // Demo-Modus: direkt URL \u00f6ffnen, damit's trotzdem funktioniert
    demoOpenApp(app);
  }
}

function demoOpenApp(app) {
  const urls = {
    spotify: 'https://open.spotify.com',
    youtube: 'https://youtube.com',
    github:  'https://github.com',
    discord: 'https://discord.com/app',
    netflix: 'https://netflix.com',
    twitch:  'https://twitch.tv',
    gmail:   'https://mail.google.com',
    maps:    'https://maps.google.com',
    chatgpt: 'https://chat.openai.com',
    claude:  'https://claude.ai',
  };
  const url = urls[app] || `https://www.google.com/search?q=${encodeURIComponent(app)}`;
  showSubtitle(`\u00d6ffne ${app}...`);
  window.open(url, '_blank');
}

// ---------- Icon-Management ----------------------------------------------
function addIcon(app, label) {
  // Vermeide Duplikate
  if (state.icons.find(i => i.app === app)) return;
  const meta = appMeta(app);
  const icon = {
    id: `icon-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,
    app,
    label: label || meta.label,
    emoji: meta.emoji,
    color: meta.color,
    // Zuf\u00e4llige Spawn-Position im mittleren Drittel
    x: window.innerWidth  * (0.3 + Math.random() * 0.4),
    y: window.innerHeight * (0.3 + Math.random() * 0.3),
    vx: 0, vy: 0,
    size: 90,
    spawnTime: performance.now(),
    heldBy: null,      // Index der Hand die es gerade h\u00e4lt
    hoveredSince: 0,   // timestamp ab wann ein Finger auf dem Icon ist
    activating: false,
  };
  state.icons.push(icon);
  updateIconCount();
}

function removeIcon(app) {
  state.icons = state.icons.filter(i => i.app !== app);
  updateIconCount();
}

function updateIconCount() {
  iconCount.textContent = String(state.icons.length);
}

function showSubtitle(text) {
  subtitle.textContent = text;
  subtitle.classList.add('visible');
  clearTimeout(subtitle._timer);
  subtitle._timer = setTimeout(() => subtitle.classList.remove('visible'), 3500);
}

// ---------- MediaPipe Hands Setup ----------------------------------------
// Wird in startApp() initialisiert, weil es erst nach Permission sinnvoll ist.
let hands;

function setupHands() {
  hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
  });
  hands.setOptions({
    maxNumHands: 2,
    modelComplexity: 1,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.6,
  });
  hands.onResults(onHandResults);
}

function onHandResults(results) {
  // Video-Bild selbst wird vom <video>-Element gerendert, wir malen nur das Overlay.
  state.hands = results.multiHandLandmarks || [];
}

// ---------- Hauptloop: Rendering, Physik, Gestenerkennung ----------------
function render(now) {
  // FPS
  if (state.lastFrameTime) {
    const dt = now - state.lastFrameTime;
    state.fps = Math.round(1000 / dt);
    fpsEl.textContent = state.fps;
  }
  state.lastFrameTime = now;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Landmarks sind normiert (0..1), wobei 0=links. Wir spiegeln das Video,
  // also muss x zu (1-x) werden damit die gemalte Hand zu dem passt was
  // man im Spiegel sieht.
  const handsScreen = state.hands.map(lm => lm.map(pt => ({
    x: (1 - pt.x) * canvas.width,
    y: pt.y * canvas.height,
    z: pt.z,
  })));

  handStatus.textContent = handsScreen.length > 0
    ? `${handsScreen.length} HAND${handsScreen.length > 1 ? 'S' : ''} TRACKED`
    : 'NO HAND';

  // Gesten & Icon-Interaktion pro Hand
  const fingerTips = [];    // {x,y,handIdx} f\u00fcr Hover-Logik
  let anyPinch = false;
  for (let h = 0; h < handsScreen.length; h++) {
    const hand = handsScreen[h];
    drawHandSkeleton(hand);

    const thumbTip  = hand[4];
    const indexTip  = hand[8];
    const middleTip = hand[12];

    // Pinch: Abstand Daumen-Zeigefinger relativ zur Handgr\u00f6\u00dfe
    const handScale = distance(hand[0], hand[9]) || 1;
    const pinchDist = distance(thumbTip, indexTip) / handScale;
    const isPinching = pinchDist < 0.35;

    if (isPinching) anyPinch = true;

    const pinchPoint = {
      x: (thumbTip.x + indexTip.x) / 2,
      y: (thumbTip.y + indexTip.y) / 2,
    };

    // Pinch-Visualisierung
    if (isPinching) drawPinchMarker(pinchPoint);

    // Icon-Grab-Logik
    handleIconGrab(h, isPinching, pinchPoint);

    fingerTips.push({ x: indexTip.x, y: indexTip.y, handIdx: h });

    // Finger-Trail (nur wenn nicht gepincht)
    if (!isPinching) {
      state.trail.push({ x: indexTip.x, y: indexTip.y, t: now });
    }
  }
  // Trail nach 450ms verblassen lassen
  state.trail = state.trail.filter(p => now - p.t < 450);
  drawTrail(now);

  gestureEl.textContent = anyPinch ? 'PINCH' : (handsScreen.length ? 'OPEN' : '\u2014');

  // Icons zeichnen + Hover/Aktivierung
  drawIcons(now, fingerTips);

  // Partikel
  updateParticles(now);
  drawParticles();

  requestAnimationFrame(render);
}

// ---------- Zeichen-Helfer -----------------------------------------------
// Verbindungen zwischen Landmarks f\u00fcr das Hand-Skelett.
const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],       // Daumen
  [0,5],[5,6],[6,7],[7,8],       // Zeigefinger
  [5,9],[9,10],[10,11],[11,12],  // Mittelfinger
  [9,13],[13,14],[14,15],[15,16],// Ringfinger
  [13,17],[17,18],[18,19],[19,20],// Kleiner Finger
  [0,17],                         // Handballen
];

function drawHandSkeleton(hand) {
  // Glow-Linien
  ctx.lineCap = 'round';
  ctx.strokeStyle = 'rgba(0, 255, 225, 0.85)';
  ctx.shadowColor = '#00ffe1';
  ctx.shadowBlur = 12;
  ctx.lineWidth = 2.5;

  ctx.beginPath();
  for (const [a, b] of HAND_CONNECTIONS) {
    ctx.moveTo(hand[a].x, hand[a].y);
    ctx.lineTo(hand[b].x, hand[b].y);
  }
  ctx.stroke();

  // Landmark-Punkte
  ctx.shadowBlur = 8;
  ctx.fillStyle = '#ffffff';
  for (const p of hand) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.shadowBlur = 0;
}

function drawPinchMarker(p) {
  ctx.save();
  ctx.strokeStyle = '#ff3b9a';
  ctx.shadowColor = '#ff3b9a';
  ctx.shadowBlur = 20;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 24, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
  ctx.fillStyle = '#ff3b9a';
  ctx.fill();
  ctx.restore();
}

function drawTrail(now) {
  if (state.trail.length < 2) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(0, 255, 225, 0.5)';
  ctx.shadowColor = '#00ffe1';
  ctx.shadowBlur = 14;
  ctx.lineCap = 'round';
  ctx.beginPath();
  for (let i = 1; i < state.trail.length; i++) {
    const age = (now - state.trail[i].t) / 450;
    ctx.lineWidth = (1 - age) * 6;
    ctx.moveTo(state.trail[i-1].x, state.trail[i-1].y);
    ctx.lineTo(state.trail[i].x,   state.trail[i].y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawIcons(now, fingerTips) {
  for (const icon of state.icons) {
    const age = (now - icon.spawnTime) / 600;
    const spawnScale = Math.min(1, age * age * (3 - 2 * age)); // smoothstep

    // Hover-Check: n\u00e4chster Finger in Reichweite?
    let hovering = false;
    for (const tip of fingerTips) {
      const d = Math.hypot(tip.x - icon.x, tip.y - icon.y);
      if (d < icon.size / 2) { hovering = true; break; }
    }

    // Hold-Timer f\u00fcr Aktivierung (900ms)
    if (hovering && !icon.heldBy) {
      if (!icon.hoveredSince) icon.hoveredSince = now;
      const held = now - icon.hoveredSince;
      if (held > 900 && !icon.activating) {
        icon.activating = true;
        activateIcon(icon);
      }
    } else {
      icon.hoveredSince = 0;
    }

    const holdProgress = icon.hoveredSince
      ? Math.min(1, (now - icon.hoveredSince) / 900)
      : 0;

    // Schweben
    const floatY = icon.heldBy === null ? Math.sin(now / 600 + icon.x) * 4 : 0;
    const drawX = icon.x;
    const drawY = icon.y + floatY;
    const scale = spawnScale * (icon.heldBy !== null ? 1.1 : 1.0);
    const r = (icon.size / 2) * scale;

    ctx.save();

    // Au\u00dferer Glow-Ring
    ctx.strokeStyle = icon.color;
    ctx.shadowColor = icon.color;
    ctx.shadowBlur = icon.heldBy !== null ? 30 : 18;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.8;
    ctx.beginPath();
    ctx.arc(drawX, drawY, r, 0, Math.PI * 2);
    ctx.stroke();

    // F\u00fcllung (halbtransparent)
    ctx.globalAlpha = hovering ? 0.35 : 0.2;
    ctx.fillStyle = icon.color;
    ctx.beginPath();
    ctx.arc(drawX, drawY, r - 4, 0, Math.PI * 2);
    ctx.fill();

    // Hold-Progress-Bogen
    if (holdProgress > 0) {
      ctx.globalAlpha = 1;
      ctx.strokeStyle = '#ffffff';
      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur = 20;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(drawX, drawY, r + 8, -Math.PI / 2,
              -Math.PI / 2 + holdProgress * Math.PI * 2);
      ctx.stroke();
    }

    // Emoji / Symbol
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${Math.round(r * 0.9)}px 'Orbitron', sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon.emoji, drawX, drawY);

    // Label
    ctx.font = `500 11px 'JetBrains Mono', monospace`;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.fillText(icon.label.toUpperCase(), drawX, drawY + r + 18);

    ctx.restore();
  }
}

function handleIconGrab(handIdx, isPinching, pinchPoint) {
  if (isPinching) {
    // Gibt's schon ein Icon das diese Hand h\u00e4lt?
    const held = state.icons.find(i => i.heldBy === handIdx);
    if (held) {
      held.x = pinchPoint.x;
      held.y = pinchPoint.y;
      return;
    }
    // Sonst: Icon suchen das nah genug am Pinch-Punkt ist
    let nearest = null, nearestD = Infinity;
    for (const icon of state.icons) {
      if (icon.heldBy !== null) continue;
      const d = Math.hypot(icon.x - pinchPoint.x, icon.y - pinchPoint.y);
      if (d < icon.size / 2 && d < nearestD) {
        nearest = icon; nearestD = d;
      }
    }
    if (nearest) {
      nearest.heldBy = handIdx;
      nearest.hoveredSince = 0;
      nearest.activating = false;
    }
  } else {
    // Loslassen: alle Icons die diese Hand hielt freigeben
    for (const icon of state.icons) {
      if (icon.heldBy === handIdx) icon.heldBy = null;
    }
  }
}

function activateIcon(icon) {
  // Partikel-Explosion als Feedback
  for (let i = 0; i < 30; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 2 + Math.random() * 4;
    state.particles.push({
      x: icon.x, y: icon.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 1.0,
      color: icon.color,
    });
  }
  showSubtitle(`>> ${icon.label.toUpperCase()} AKTIVIERT`);
  sendClick(icon.app);

  // Icon entfernen nach kurzer Verz\u00f6gerung
  setTimeout(() => {
    state.icons = state.icons.filter(i => i.id !== icon.id);
    updateIconCount();
  }, 300);
}

// ---------- Partikel-System (reines Eye-Candy) ---------------------------
function updateParticles() {
  for (const p of state.particles) {
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.15;
    p.life -= 0.02;
  }
  state.particles = state.particles.filter(p => p.life > 0);
}

function drawParticles() {
  ctx.save();
  for (const p of state.particles) {
    ctx.globalAlpha = p.life;
    ctx.fillStyle = p.color;
    ctx.shadowColor = p.color;
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

// ---------- Utils --------------------------------------------------------
function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

// ---------- Start-Flow ---------------------------------------------------
async function startApp() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 1280, height: 720, facingMode: 'user' },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();

    setupHands();

    // MediaPipe's Camera-Util schickt uns pro Frame ein Bild.
    const camera = new Camera(video, {
      onFrame: async () => {
        if (hands) await hands.send({ image: video });
      },
      width: 1280,
      height: 720,
    });
    camera.start();

    startPanel.classList.add('hidden');
    connectWS();
    requestAnimationFrame(render);

    // Demo-Icons falls kein Backend da ist \u2013 nach 2s einblenden,
    // damit man auch ohne Python was zum Anfassen hat.
    setTimeout(() => {
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        ['spotify', 'youtube', 'github'].forEach(addIcon);
        showSubtitle('DEMO: 3 ICONS BEREIT');
      }
    }, 2000);

  } catch (err) {
    alert('Kamera-Zugriff fehlgeschlagen: ' + err.message);
  }
}

startBtn.addEventListener('click', startApp);
