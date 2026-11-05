"use strict";

const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const State = {
  bootstrap: null,
  session: null,
  hiddenScenes: [],
  current: null,
  setup: {},
  score: 0,
  sound: true,
  view: "games",
  topic: "animal",
  items: [],
  visible: 30,
  topicCache: new Map(),
  cleanup: null,
  timer: null,
  remaining: 0,
  sessionClock: null,
  sessionTimer: null,
  sessionExpired: false,
};
const UI = {
  games: $("#gamesView"),
  library: $("#libraryView"),
  design: $("#designView"),
  game: $("#gameView"),
  grid: $("#gameGrid"),
  stage: $("#stage"),
  modal: $("#setupModal"),
  detail: $("#detailModal"),
  topics: $("#topicTabs"),
  libraryGrid: $("#libraryGrid"),
  search: $("#librarySearch"),
  toast: $("#toast"),
};
const META = {
  "listen-image-en": {
    group: "learning",
    color: "#1b7f8d",
    desc: "Nghe phát âm tiếng Anh và chọn đúng hình.",
  },
  "listen-image-vi": {
    group: "learning",
    color: "#25755e",
    desc: "Nghe tên tiếng Việt và nhận biết hình ảnh.",
  },
  puzzle: {
    group: "thinking",
    color: "#795aa8",
    desc: "Quan sát mẫu và ghép các mảnh về đúng vị trí.",
  },
  sudoku: {
    group: "thinking",
    color: "#9b6b35",
    desc: "Điền số theo hàng, cột và vùng không lặp lại.",
  },
  "image-answer": {
    group: "learning",
    color: "#355e9b",
    desc: "Nhìn hình và chọn tên gọi chính xác.",
  },
  count: {
    group: "learning",
    color: "#9b7135",
    desc: "Đếm số lượng vật thể và chọn đáp án.",
  },
  "alphabet-en": {
    group: "learning",
    color: "#8d3f6e",
    desc: "Học mặt chữ và cách đọc bảng chữ cái tiếng Anh.",
  },
  "alphabet-vi": {
    group: "learning",
    color: "#436eaa",
    desc: "Học bảng chữ cái tiếng Việt cùng dấu đặc trưng.",
  },
  memory: {
    group: "thinking",
    color: "#6152a5",
    desc: "Lật thẻ, ghi nhớ và tìm các cặp giống nhau.",
  },
  bomber: {
    group: "thinking",
    color: "#9a4941",
    desc: "Dò mìn trên máy tính, mở ô an toàn và đánh dấu vị trí có bom.",
  },
  "hidden-object": {
    group: "thinking",
    color: "#437f67",
    desc: "Tìm đủ các vật mẫu đang ẩn trong bức tranh.",
  },
  "tic-tac-toe": {
    group: "thinking",
    color: "#59647f",
    desc: "Cờ caro vô hạn cho hai người, kéo bàn cờ và nối năm quân để thắng.",
  },
  colors: {
    group: "learning",
    color: "#9a3f5d",
    desc: "Nhận biết, nghe tên và luyện phản xạ với màu sắc.",
  },
  "space-shooter": {
    group: "action",
    color: "#3a4c9b",
    desc: "Phi thuyền tự động bắn, nhặt vật phẩm, tem thưởng và nâng cấp.",
  },
  "math-basic": {
    group: "learning",
    color: "#367a74",
    desc: "Luyện cộng, trừ và so sánh số cơ bản.",
  },
  "math-advanced": {
    group: "learning",
    color: "#77548e",
    desc: "Luyện nhân, chia và bài toán nhiều bước.",
  },
  "match-transport": {
    group: "learning",
    color: "#2f718c",
    desc: "Nối phương tiện với đường bộ, đường thủy hoặc hàng không.",
  },
  "match-habitat": {
    group: "learning",
    color: "#4d7f48",
    desc: "Nối động vật với môi trường sống phù hợp.",
  },
};
const TOPIC_ICONS = {
  animal: "🦁",
  transport: "🚗",
  plant: "🍎",
  object: "🎸",
  flag: "🏳️",
  number: "123",
  "alphabet-en": "ABC",
  "alphabet-vi": "ĂÂ",
  environment: "🌍",
};

const escapeHtml = (v = "") =>
  String(v).replace(
    /[&<>'"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        c
      ],
  );
const shuffle = (input) => {
  const a = [...input];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};
const asset = (p) => (p ? "/resource/" + p : "");
const thumb = (p) => (p ? "/thumb/" + p : "");
const showToast = (text) => {
  UI.toast.textContent = text;
  UI.toast.classList.add("show");
  clearTimeout(showToast.t);
  showToast.t = setTimeout(() => UI.toast.classList.remove("show"), 1800);
};
let gameEpoch = 0;
const pending = new Set();
const later = (fn, ms = 0) => {
  const epoch = gameEpoch;
  const id = setTimeout(() => {
    pending.delete(id);
    if (epoch === gameEpoch) fn();
  }, ms);
  pending.add(id);
  return id;
};
const profile = () =>
  State.bootstrap?.education.profiles.find(
    (p) => p.id === (State.profile || State.session?.profile),
  ) || State.bootstrap?.education.profiles[1];
const guide = (id) => State.bootstrap?.education.guides[id];
const gameTitle = (g) => guide(g.id)?.title || g.name.vi;
const abortOld = (epoch) => {
  if (epoch !== gameEpoch)
    throw new DOMException("Lượt đã kết thúc", "AbortError");
};
const closeModal = (m) => {
  m.classList.remove("show");
  State.returnFocus?.focus();
};
function showModal(m) {
  State.returnFocus = document.activeElement;
  m.classList.add("show");
  m.querySelector("button,select")?.focus();
}
const progress = { rounds: 0, games: new Set() };
const setScore = (n) => {
  $("#score").textContent = State.score = n;
};
const AudioSystem = {
  ctx: null,
  musicGain: null,
  sfxGain: null,
  musicTimer: null,
  step: 0,
  ensure() {
    if (!this.ctx) {
      const C = window.AudioContext || window.webkitAudioContext;
      if (!C) return;
      this.ctx = new C();
      this.musicGain = this.ctx.createGain();
      this.sfxGain = this.ctx.createGain();
      this.musicGain.gain.value = 0.032;
      this.sfxGain.gain.value = 0.18;
      this.musicGain.connect(this.ctx.destination);
      this.sfxGain.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
  },
  tone(
    freq,
    duration = 0.12,
    type = "sine",
    volume = 0.5,
    when = 0,
    bus = "sfx",
  ) {
    if (!State.sound) return;
    this.ensure();
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when,
      o = this.ctx.createOscillator(),
      g = this.ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(volume, t + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, t + duration);
    o.connect(g);
    g.connect(bus === "music" ? this.musicGain : this.sfxGain);
    o.start(t);
    o.stop(t + duration + 0.03);
  },
  effect(kind) {
    if (kind === "success") {
      this.tone(523, 0.13, "sine", 0.6);
      this.tone(659, 0.16, "sine", 0.55, 0.1);
      this.tone(784, 0.22, "sine", 0.5, 0.2);
    } else if (kind === "found" || kind === "correct") {
      this.tone(660, 0.09, "triangle", 0.42);
      this.tone(880, 0.14, "triangle", 0.34, 0.07);
    } else if (kind === "shot") {
      this.tone(330, 0.045, "square", 0.08);
    } else if (kind === "meteor") {
      this.tone(92, 0.13, "sawtooth", 0.25);
      this.tone(180, 0.08, "triangle", 0.18, 0.03);
    } else if (kind === "damage") {
      this.tone(120, 0.28, "sawtooth", 0.5);
      this.tone(75, 0.32, "triangle", 0.35, 0.04);
    } else this.tone(190, 0.16, "triangle", 0.34);
  },
  startMusic() {
    if (!State.sound || this.musicTimer) return;
    this.ensure();
    const notes = [261.63, 329.63, 392, 329.63, 293.66, 349.23, 440, 349.23];
    const play = () => {
      if (!State.sound) return;
      const root = notes[this.step++ % notes.length];
      this.tone(root, 1.9, "sine", 0.34, 0, "music");
      this.tone(root / 2, 2.3, "sine", 0.2, 0, "music");
    };
    play();
    this.musicTimer = setInterval(play, 2200);
  },
  stopMusic() {
    clearInterval(this.musicTimer);
    this.musicTimer = null;
  },
  setEnabled(on) {
    if (on) this.startMusic();
    else {
      this.stopMusic();
      window.speechSynthesis?.cancel();
    }
  },
};
const reward = (n = 10, text = "Chính xác!") => {
  AudioSystem.effect("correct");
  setScore(State.score + n);
  showToast(text + " · +" + n);
};
const miss = (text = "Thử lại nhé!") => {
  AudioSystem.effect("wrong");
  showToast(text);
};
const makeUtterance = (text, lang = "vi-VN") => {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = lang.startsWith("en") ? 0.78 : 0.82;
  const voice = speechSynthesis
    .getVoices()
    .find((v) =>
      v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()),
    );
  if (voice) u.voice = voice;
  return u;
};
const speak = (text, lang = "vi-VN") => {
  if (!State.sound || !text || !window.speechSynthesis) return;
  window.speechSynthesis?.cancel();
  speechSynthesis.speak(makeUtterance(text, lang));
};
const speakAsync = (text, lang = "vi-VN") =>
  new Promise((resolve) => {
    if (!State.sound || !text || !window.speechSynthesis) return resolve();
    window.speechSynthesis?.cancel();
    const u = makeUtterance(text, lang),
      done = () => resolve();
    u.onend = done;
    u.onerror = done;
    speechSynthesis.speak(u);
    setTimeout(done, 2600);
  });
const itemSpeechText = (item, lang = "vi") => {
  if (!item) return "";
  const english = lang === "en",
    parts = [
      english ? item.enName : item.viName,
      english ? item.descriptionEn : item.description,
    ];
  (item.facts || []).forEach((f) =>
    parts.push(
      (english ? f.labelEn : f.label) + ". " + (english ? f.valueEn : f.value),
    ),
  );
  return parts.filter(Boolean).join(". ");
};
const speakItem = (item, lang = "vi") =>
  speak(itemSpeechText(item, lang), lang === "en" ? "en-US" : "vi-VN");
const FACT_ICONS = {
  category: "●",
  home: "⌂",
  globe: "◎",
  food: "◆",
  check: "✓",
  eye: "◉",
  road: "↔",
  bolt: "⚡",
  shield: "★",
  leaf: "☘",
  water: "≈",
  clock: "◷",
  size: "↕",
  speed: "➜",
  sound: "♫",
};
const factIcon = (f) =>
  FACT_ICONS[String(f?.icon || "").toLowerCase()] || f?.icon || "✦";
const allowedGame = (id) =>
  !State.sessionExpired && !!State.session?.games?.some((g) => g.id === id);

async function fetchSession() {
  const token = new URLSearchParams(location.search).get("session");
  if (!token) return null;
  try {
    const response = await fetch("/api/sessions/" + encodeURIComponent(token), {
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok || !data.ok)
      throw Error(data.message || "Phiên không hợp lệ");
    return {
      token,
      profile: data.config.profile || "early-primary",
      games: data.config.games || [],
      expiresAt: data.expires_at,
      serverNow: data.server_now,
      status: data.status,
    };
  } catch (error) {
    showToast(error.message);
    return { error: error.message, games: [] };
  }
}

async function init() {
  try {
    const [bootstrap, session, hiddenData] = await Promise.all([
      fetch("/api/bootstrap").then((r) => r.json()),
      fetchSession(),
      fetch("/resource/hidden-scenes-v87.json", { cache: "no-store" }).then(
        (r) => r.json(),
      ),
    ]);
    State.bootstrap = bootstrap;
    State.session = session;
    State.hiddenScenes = hiddenData.scenes || [];
    $("#resourceCount").textContent =
      bootstrap.manifest?.counts?.items || "500+";
    if (State.session && !State.session.error)
      State.sessionClock = new GOTSessionClock(
        State.session.expiresAt,
        State.session.serverNow,
      );
    const picker = $("#profilePicker");
    bootstrap.education.profiles.forEach((p) =>
      picker.add(new Option(p.name + " · " + p.ages, p.id)),
    );
    picker.value = session?.profile || "early-primary";
    State.profile = picker.value;
    picker.onchange = () => {
      State.profile = picker.value;
      renderGames($(".filter.active")?.dataset.filter || "all");
    };
    renderSession();
    renderGames();
    renderTopics();
    renderDesign();
    bind();
    startSessionMonitor();
  } catch (error) {
    UI.grid.innerHTML =
      '<div class="result-box"><h2>Không tải được dữ liệu</h2><p>' +
      escapeHtml(error.message) +
      "</p></div>";
  }
}
function bind() {
  const unlockAudio = () => {
    AudioSystem.ensure();
    AudioSystem.startMusic();
  };
  addEventListener("pointerdown", unlockAudio, { once: true });
  addEventListener("keydown", unlockAudio, { once: true });
  $$(".nav-button").forEach(
    (b) => (b.onclick = () => switchView(b.dataset.view)),
  );
  $$(".filter").forEach(
    (b) =>
      (b.onclick = () => {
        $$(".filter").forEach((x) => x.classList.toggle("active", x === b));
        renderGames(b.dataset.filter);
      }),
  );
  $("#soundButton").onclick = () => {
    $("#soundButton").textContent = (State.sound = !State.sound) ? "🔊" : "🔇";
    AudioSystem.setEnabled(State.sound);
  };
  $("#backButton").onclick = () => switchView("games");
  $("#startButton").onclick = startCurrentGame;
  $$("[data-close]").forEach(
    (b) => (b.onclick = () => closeModal($("#" + b.dataset.close))),
  );
  $("#helpButton").onclick = () => openSetup(State.current, true);
  document.addEventListener("keydown", (e) => {
    const modal = $(".modal.show");
    if (!modal) return;
    if (e.key === "Escape") {
      closeModal(modal);
      window.speechSynthesis?.cancel();
    }
    if (e.key === "Tab") {
      const buttons = [
          ...modal.querySelectorAll(
            "button:not([disabled]),select,input,a[href]",
          ),
        ].filter((x) => x.getClientRects().length),
        first = buttons[0],
        last = buttons.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
  UI.search.oninput = renderLibrary;
  $("#loadMore").onclick = () => {
    State.visible += 30;
    renderLibrary();
  };
  $("#randomItem").onclick = () => {
    const list = filteredItems();
    if (list.length) openDetail(list[Math.floor(Math.random() * list.length)]);
  };
  $("#speakVi").onclick = () => speakItem(State.detailItem, "vi");
  $("#speakEn").onclick = () => speakItem(State.detailItem, "en");
  $("#detailEnglish").onclick = () => speak(State.detailItem?.enName, "en-US");
  $("#speakDescriptionVi").onclick = () =>
    speak(State.detailItem?.description, "vi-VN");
  $("#speakDescriptionEn").onclick = () =>
    speak(State.detailItem?.descriptionEn, "en-US");
  $("#stopSpeech").onclick = () => window.speechSynthesis?.cancel();
  $("#nextDetail").onclick = () => {
    const list = filteredItems(),
      i = list.indexOf(State.detailItem);
    if (list.length) openDetail(list[(i + 1) % list.length]);
  };
}
function renderSession() {
  const chip = $("#sessionChip"),
    notice = $("#sessionNotice");
  if (State.session && !State.session.error && State.session.games.length) {
    chip.textContent =
      State.session.games.length +
      " trò · còn " +
      formatTime(State.sessionClock?.remaining() || 0);
    chip.className = "session-chip active";
    notice.hidden = true;
  } else {
    chip.textContent = State.session?.error || "Chưa mở phiên chơi";
    chip.className = "session-chip error";
    notice.hidden = false;
  }
}
function switchView(view) {
  stopGame();
  State.view = view;
  [UI.games, UI.library, UI.design, UI.game].forEach((x) =>
    x.classList.remove("active"),
  );
  (
    ({
      games: UI.games,
      library: UI.library,
      design: UI.design,
      game: UI.game,
    })[view] || UI.games
  ).classList.add("active");
  $$(".nav-button").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === view),
  );
  if (view === "library" && !State.items.length) loadTopic(State.topic);
  scrollTo({ top: 0, behavior: "smooth" });
}
function renderGames(filter = "all") {
  UI.grid.innerHTML = "";
  $("#profileNote").textContent = profile().name + " · " + profile().note;
  State.bootstrap.games
    .filter(
      (g) =>
        g.enabled !== false &&
        (filter === "all" ||
          (filter === "recommended" && profile().recommended.includes(g.id)) ||
          META[g.id]?.group === filter),
    )
    .forEach((g, i) => {
      const locked = !allowedGame(g.id),
        m = META[g.id] || {
          group: "learning",
          color: "#35677d",
          desc: "Một thử thách đang chờ bạn.",
        },
        b = document.createElement("button");
      b.className = "game-card" + (locked ? " locked" : "");
      b.style.setProperty("--card", m.color);
      b.innerHTML =
        '<span class="game-index">' +
        String(i + 1).padStart(2, "0") +
        " · " +
        (profile().recommended.includes(g.id)
          ? "HỢP VỚI CON"
          : { learning: "HỌC TẬP", thinking: "TƯ DUY", action: "PHỐI HỢP" }[
              m.group
            ]) +
        '</span><span class="game-icon">' +
        escapeHtml(guide(g.id)?.icon || g.icon || "🎮") +
        "</span><h3>" +
        escapeHtml(gameTitle(g)) +
        "</h3><p>" +
        escapeHtml(guide(g.id)?.goal || m.desc) +
        "</p><footer>" +
        (locked ? "MỞ PHIÊN ĐỂ CHƠI" : "CHƠI NGAY") +
        " <span>" +
        (locked ? "🔒" : "→") +
        "</span></footer>";
      b.onclick = () =>
        locked ? showToast("Hãy mở phiên để chơi tất cả trò") : openSetup(g);
      UI.grid.appendChild(b);
    });
}
function openSetup(game, help = false) {
  State.current = game;
  if (!help)
    State.setup = {
      difficulty: profile().difficulty,
      topic: State.bootstrap.topics[0]?.id || "animal",
    };
  $("#setupIcon").textContent = guide(game.id)?.icon || game.icon || "🎮";
  $("#setupTitle").textContent = gameTitle(game);
  $("#setupDescription").textContent = guide(game.id)?.goal || "";
  const g = guide(game.id);
  $("#setupGuide").innerHTML =
    "<ol>" +
    g.steps.map((x) => "<li>" + escapeHtml(x) + "</li>").join("") +
    "</ol><p><b>Thao tác:</b> " +
    escapeHtml(g.controls) +
    "</p><details><summary>Gợi ý cho người lớn</summary><p>" +
    escapeHtml(g.parent) +
    "</p></details>";
  $("#startButton").textContent = help
    ? "Tiếp tục lượt đang chơi"
    : "Sẵn sàng, bắt đầu →";
  $("#startButton").onclick = help
    ? () => closeModal(UI.modal)
    : startCurrentGame;
  const fields = $("#setupFields");
  fields.innerHTML = "";
  fields.hidden = help;
  if (game.topicSelectable)
    addSelect(
      "topic",
      "Chủ đề",
      State.bootstrap.topics
        .filter((t) =>
          ["animal", "transport", "plant", "object", "flag"].includes(t.id),
        )
        .map((t) => [t.id, t.name.vi]),
    );
  if (game.difficultySelectable)
    addSelect("difficulty", "Cấp độ", [
      ["easy", "Dễ"],
      ["normal", "Vừa"],
      ["hard", "Khó"],
    ]);
  const p = document.createElement("p");
  p.className = "instruction";
  p.textContent =
    "Dùng chung thời gian phiên · còn " +
    formatTime(State.sessionClock?.remaining() || 0);
  fields.appendChild(p);
  showModal(UI.modal);
}
function addSelect(name, label, options) {
  const l = document.createElement("label"),
    s = document.createElement("select");
  l.textContent = label;
  s.name = name;
  options.forEach(([v, t]) => s.add(new Option(t, v)));
  s.onchange = () => (State.setup[name] = s.value);
  s.value = State.setup[name] || s.value;
  State.setup[name] = s.value;
  l.appendChild(s);
  $("#setupFields").appendChild(l);
}
async function startCurrentGame() {
  if (State.sessionClock?.remaining() <= 0 || !allowedGame(State.current?.id))
    return expireSession();
  UI.modal.classList.remove("show");
  switchView("game");
  setScore(0);
  AudioSystem.startMusic();
  $("#gameTitle").textContent = gameTitle(State.current);
  $("#learningGoal").textContent = guide(State.current.id).goal;
  $("#gameMeta").textContent =
    ["Dễ", "Vừa", "Khó"][
      ["easy", "normal", "hard"].indexOf(State.setup.difficulty)
    ] || "";
  const id = State.current.id;
  startTimer();
  const epoch = gameEpoch;
  try {
    if (id === "listen-image-en") return await quizGame("listen", "en");
    if (id === "listen-image-vi") return await quizGame("listen", "vi");
    if (id === "image-answer") return await quizGame("image", "vi");
    if (id === "count") return await countGame();
    if (id === "puzzle") return await puzzleGame();
    if (id === "sudoku") return await sudokuGame();
    if (id === "alphabet-en") return await alphabetGame("en");
    if (id === "alphabet-vi") return await alphabetGame("vi");
    if (id === "memory") return await memoryGame();
    if (id === "bomber") return await bomberGame();
    if (id === "hidden-object") return await hiddenObjectGame();
    if (id === "tic-tac-toe") return await ticTacToe();
    if (id === "colors") return await colorGame();
    if (id === "space-shooter") return await spaceShooter();
    if (id === "math-basic") return await mathGame(false);
    if (id === "math-advanced") return await mathGame(true);
    if (id === "match-transport") return await matchGame("transport");
    if (id === "match-habitat") return await matchGame("habitat");
  } catch (error) {
    if (error.name === "AbortError" || epoch !== gameEpoch) return;
    UI.stage.innerHTML =
      '<div class="result-box"><h2>Chưa mở được trò chơi</h2><p>Kiểm tra kết nối rồi thử lại. Thời gian phiên vẫn giữ nguyên.</p><button id="retryGame" class="primary-button">Thử lại</button></div>';
    $("#retryGame").onclick = startCurrentGame;
    console.warn("Game unavailable:", id, error.message);
  }
}
function formatTime(seconds) {
  return (
    String(Math.floor(seconds / 60)).padStart(2, "0") +
    ":" +
    String(seconds % 60).padStart(2, "0")
  );
}
function expireSession() {
  if (State.sessionExpired) return;
  State.sessionExpired = true;
  clearInterval(State.sessionTimer);
  clearInterval(State.timer);
  State.session.error = "Phiên đã hết thời gian. Người lớn cần mở phiên mới.";
  UI.modal.classList.remove("show");
  UI.detail.classList.remove("show");
  switchView("games");
  renderSession();
  renderGames();
  showToast(State.session.error);
}
function startSessionMonitor() {
  clearInterval(State.sessionTimer);
  if (!State.sessionClock) return;
  const tick = () => {
    if (State.sessionClock.remaining() <= 0) return expireSession();
    renderSession();
  };
  tick();
  if (!State.sessionExpired) State.sessionTimer = setInterval(tick, 1000);
  document.addEventListener("visibilitychange", tick);
  addEventListener("pageshow", tick);
}
function startTimer() {
  clearInterval(State.timer);
  const tick = () => {
    State.remaining = State.sessionClock?.remaining() || 0;
    $("#gameTime").textContent = formatTime(State.remaining);
    if (State.remaining <= 0) expireSession();
  };
  tick();
  if (!State.sessionExpired) State.timer = setInterval(tick, 1000);
}
function stopGame() {
  gameEpoch++;
  pending.forEach(clearTimeout);
  pending.clear();
  clearInterval(State.timer);
  State.timer = null;
  AudioSystem.stopMusic();
  if (State.cleanup)
    try {
      State.cleanup();
    } catch {}
  State.cleanup = null;
  window.speechSynthesis?.cancel();
  if (UI.stage) UI.stage.innerHTML = "";
}
function finishGame(won, title) {
  gameEpoch++;
  pending.forEach(clearTimeout);
  pending.clear();
  progress.rounds++;
  progress.games.add(State.current.id);
  $("#learningProgress").textContent =
    "Đã khám phá " +
    progress.games.size +
    " trò · hoàn thành " +
    progress.rounds +
    " lượt trong trang này. Hãy nghỉ mắt và kể một điều vừa học!";
  clearInterval(State.timer);
  if (State.cleanup)
    try {
      State.cleanup();
    } catch {}
  State.cleanup = null;
  UI.stage.innerHTML =
    '<div class="result-box"><div class="result-icon">' +
    (won ? "🏆" : "⏱️") +
    "</div><h2>" +
    escapeHtml(title) +
    '</h2><p class="instruction">Lượt này: ' +
    State.score +
    ' điểm. Cùng nói lại một điều vừa học, rồi nghỉ mắt một chút nhé!</p><div class="result-actions"><button id="againButton" class="primary-button">Chơi lại</button><button id="listButton" class="secondary-button">Danh sách trò</button></div></div>';
  $("#againButton").onclick = startCurrentGame;
  $("#listButton").onclick = () => switchView("games");
}
async function topicData(id) {
  const entry = State.topicCache.get(id);
  if (entry && Date.now() - entry.time < 60000) return entry.promise;
  const promise = fetch("/api/topic/" + encodeURIComponent(id), {
    cache: "no-cache",
  })
    .then((r) => {
      if (!r.ok) throw Error("Không tải được chủ đề");
      return r.json();
    })
    .catch((error) => {
      State.topicCache.delete(id);
      throw error;
    });
  State.topicCache.set(id, { time: Date.now(), promise });
  return promise;
}
const validItems = (d) =>
  (d.items || []).filter(
    (x) => x.enabled !== false && x.image && x.viName && x.enName,
  );
async function getGameItems(n = 12) {
  const epoch = gameEpoch,
    d = await topicData(State.setup.topic || "animal");
  abortOld(epoch);
  const items = shuffle(validItems(d)).slice(0, n);
  if (!items.length) throw Error("Chủ đề chưa có ảnh");
  return items;
}

async function quizGame(mode, language) {
  const pool = await getGameItems(20),
    rounds =
      State.setup.difficulty === "hard"
        ? 12
        : State.setup.difficulty === "normal"
          ? 9
          : 6;
  let round = 0,
    timerStarted = mode !== "image";
  const next = async () => {
    if (round >= rounds) return finishGame(true, "Hoàn thành thử thách!");
    let answered = false;
    const epoch = gameEpoch;
    const correct = pool[round % pool.length],
      choices = shuffle([
        correct,
        ...shuffle(pool.filter((x) => x !== correct)).slice(
          0,
          profile().choices - 1,
        ),
      ]),
      name = language === "en" ? correct.enName : correct.viName;
    UI.stage.innerHTML =
      '<div class="game-panel"><span class="eyebrow">CÂU ' +
      (round + 1) +
      " / " +
      rounds +
      "</span><h2>" +
      (mode === "listen" ? "Nghe và chọn hình" : "Hình này tên là gì?") +
      "</h2>" +
      (mode === "listen"
        ? '<button id="listenPrompt" class="primary-button">🔊 Nghe lại</button>'
        : '<img class="main-picture" src="' +
          asset(correct.image) +
          '" alt="">') +
      '<div class="' +
      (mode === "listen" ? "choice-grid" : "answer-grid") +
      '">' +
      choices
        .map(
          (x, i) =>
            '<button class="' +
            (mode === "listen" ? "choice" : "answer") +
            '" data-i="' +
            i +
            '">' +
            (mode === "listen"
              ? '<img src="' +
                thumb(x.image) +
                '" alt=""><b>' +
                escapeHtml(language === "en" ? x.enName : x.viName) +
                "</b>"
              : escapeHtml(language === "en" ? x.enName : x.viName)) +
            "</button>",
        )
        .join("") +
      "</div></div>";
    if (mode === "listen") {
      const say = () => speak(name, language === "en" ? "en-US" : "vi-VN");
      $("#listenPrompt").onclick = say;
      later(say, 250);
    }
    if (mode === "image") {
      const audio = document.createElement("button");
      audio.className = "secondary-button";
      audio.textContent = "🔊 Nghe các đáp án";
      audio.onclick = async () => {
        audio.disabled = true;
        for (const x of choices) {
          await speakAsync(x.viName, "vi-VN");
          if (epoch !== gameEpoch || answered) return;
        }
        audio.disabled = false;
      };
      $(".game-panel").appendChild(audio);
    }
    $$("[data-i]").forEach(
      (b, i) =>
        (b.onclick = () => {
          if (answered) return;
          if (choices[i] === correct) {
            answered = true;
            $$("[data-i]").forEach((x) => (x.disabled = true));
            b.classList.add("correct");
            reward(20);
            round++;
            later(next, 450);
          } else miss("Chưa đúng, hãy quan sát lại");
        }),
    );
  };
  next();
}
function countGame() {
  let round = 0;
  const total = 6,
    icons = ["🍎", "⭐", "🐟", "🚗", "🌼", "🎈"];
  const next = () => {
    if (round >= total) return finishGame(true, "Đã hoàn thành lượt đếm!");
    let answered = false;
    const max =
        profile().id === "preschool"
          ? 5
          : State.setup.difficulty === "hard"
            ? 20
            : 10,
      answer = 1 + Math.floor(Math.random() * max),
      icon = icons[round % icons.length],
      choices = numberChoices(answer, profile().choices, 1);
    UI.stage.innerHTML =
      '<div class="game-panel"><span class="eyebrow">CÂU ' +
      (round + 1) +
      " / " +
      total +
      '</span><h2>Có bao nhiêu hình?</h2><p class="instruction">Chạm từng hình để đánh dấu đã đếm.</p><div class="count-objects">' +
      Array.from(
        { length: answer },
        (_, i) =>
          '<button class="count-object" aria-label="Đánh dấu hình ' +
          (i + 1) +
          '" aria-pressed="false">' +
          icon +
          "</button>",
      ).join("") +
      '</div><div class="answer-grid">' +
      choices.map((x) => '<button class="answer">' + x + "</button>").join("") +
      "</div></div>";
    $$(".count-object").forEach(
      (b) =>
        (b.onclick = () => {
          b.classList.toggle("counted");
          b.setAttribute("aria-pressed", b.classList.contains("counted"));
        }),
    );
    $$(".answer").forEach(
      (b, i) =>
        (b.onclick = () => {
          if (answered) return;
          if (choices[i] === answer) {
            answered = true;
            b.classList.add("correct");
            reward(15);
            round++;
            later(next, 650);
          } else miss("Đếm chậm lại, mỗi hình một lần nhé!");
        }),
    );
  };
  next();
}
function numberChoices(answer, count = 4, min = 0) {
  const choices = new Set([answer]);
  let offset = 1;
  while (choices.size < count) {
    if (answer - offset >= min) choices.add(answer - offset);
    if (choices.size < count) choices.add(answer + offset);
    offset++;
  }
  return shuffle([...choices]);
}

async function puzzleGame() {
  const item = (await getGameItems(1))[0],
    size =
      profile().id === "preschool" && State.setup.difficulty === "easy"
        ? 2
        : State.setup.difficulty === "hard"
          ? 4
          : 3,
    total = size * size;
  let order = shuffle([...Array(total).keys()]),
    selected = null;
  const draw = () => {
    UI.stage.innerHTML =
      '<div class="game-panel"><span class="eyebrow">GHÉP HÌNH</span><h2>' +
      escapeHtml(item.viName) +
      '</h2><img src="' +
      asset(item.image) +
      '" alt="" style="width:90px;height:70px;object-fit:contain"><p class="instruction">Chọn hai mảnh để đổi vị trí.</p><div id="puzzleBoard" style="--size:' +
      size +
      ";display:grid;grid-template-columns:repeat(" +
      size +
      ',1fr);width:min(600px,90vw);aspect-ratio:1;margin:18px auto;gap:3px">' +
      order
        .map(
          (piece, pos) =>
            '<button aria-label="Mảnh ' +
            (piece + 1) +
            ", vị trí " +
            (pos + 1) +
            '" data-pos="' +
            pos +
            '" style="border:2px solid ' +
            (selected === pos ? "var(--yellow)" : "transparent") +
            ";background-image:url(" +
            asset(item.image) +
            ");background-size:" +
            size * 100 +
            "% " +
            size * 100 +
            "%;background-position:" +
            ((piece % size) / (size - 1)) * 100 +
            "% " +
            (Math.floor(piece / size) / (size - 1)) * 100 +
            '%;border-radius:8px"></button>',
        )
        .join("") +
      "</div></div>";
    $$("[data-pos]").forEach(
      (b) =>
        (b.onclick = () => {
          const p = +b.dataset.pos;
          if (selected === null) {
            selected = p;
            draw();
          } else {
            [order[selected], order[p]] = [order[p], order[selected]];
            selected = null;
            if (order.every((v, i) => v === i)) {
              reward(100);
              draw();
              const board = $("#puzzleBoard");
              board.classList.add("puzzle-complete");
              board.insertAdjacentHTML(
                "afterend",
                '<div class="puzzle-celebration" aria-live="polite">✨ Chính xác! ✨</div>',
              );
              $$("[data-pos]").forEach((x) => (x.disabled = true));
              return later(
                () => finishGame(true, "Ghép hình hoàn chỉnh!"),
                2000,
              );
            }
            draw();
          }
        }),
    );
  };
  draw();
}
function sudokuGame() {
  const size = State.setup.difficulty === "hard" ? 6 : 4,
    boxR = size === 6 ? 2 : 2,
    boxC = size === 6 ? 3 : 2,
    solution = Array.from({ length: size }, (_, r) =>
      Array.from(
        { length: size },
        (_, c) => ((r * boxC + Math.floor(r / boxR) + c) % size) + 1,
      ),
    ),
    holes = size === 6 ? 18 : 8,
    board = solution.map((r) => [...r]);
  shuffle([...Array(size * size).keys()])
    .slice(0, holes)
    .forEach((i) => (board[Math.floor(i / size)][i % size] = 0));
  UI.stage.innerHTML =
    '<div class="game-panel"><span class="eyebrow">SUDOKU ' +
    size +
    " × " +
    size +
    '</span><h2>Điền số còn thiếu</h2><div class="sudoku-grid" style="--size:' +
    size +
    '">' +
    board
      .flatMap((row, r) =>
        row.map(
          (v, c) =>
            '<button class="sudoku-cell ' +
            (v ? "fixed" : "") +
            '" aria-label="Hàng ' +
            (r + 1) +
            " cột " +
            (c + 1) +
            '" data-r="' +
            r +
            '" data-c="' +
            c +
            '">' +
            (v || "") +
            "</button>",
        ),
      )
      .join("") +
    '</div><button id="checkSudoku" class="primary-button">Kiểm tra</button></div>';
  $$(".sudoku-cell:not(.fixed)").forEach(
    (b) =>
      (b.onclick = () => {
        const r = +b.dataset.r,
          c = +b.dataset.c;
        board[r][c] = (board[r][c] % size) + 1;
        b.textContent = board[r][c];
        b.classList.remove("wrong");
      }),
  );
  $("#checkSudoku").onclick = () => {
    let ok = true;
    $$(".sudoku-cell:not(.fixed)").forEach((b) => {
      const r = +b.dataset.r,
        c = +b.dataset.c,
        value = board[r][c],
        wrong =
          !value ||
          board[r].filter((x) => x === value).length > 1 ||
          board.filter((row) => row[c] === value).length > 1 ||
          board
            .slice(
              Math.floor(r / boxR) * boxR,
              Math.floor(r / boxR) * boxR + boxR,
            )
            .flatMap((row) =>
              row.slice(
                Math.floor(c / boxC) * boxC,
                Math.floor(c / boxC) * boxC + boxC,
              ),
            )
            .filter((x) => x === value).length > 1;
      b.classList.toggle("wrong", wrong);
      ok &&= !wrong;
    });
    if (ok) {
      reward(120);
      finishGame(true, "Sudoku chính xác!");
    } else miss("Một vài ô chưa đúng");
  };
}
async function alphabetGame(lang) {
  const letters = (
    lang === "en"
      ? "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
      : "AĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXY"
  ).split("");
  const viNames = {
    A: "a",
    Ă: "a ngắn",
    Â: "â",
    B: "bê",
    C: "xê",
    D: "dê",
    Đ: "đê",
    E: "e",
    Ê: "ê",
    G: "giê",
    H: "hát",
    I: "i",
    K: "ca",
    L: "e lờ",
    M: "em mờ",
    N: "en nờ",
    O: "o",
    Ô: "ô",
    Ơ: "ơ",
    P: "pê",
    Q: "quy",
    R: "e rờ",
    S: "ét",
    T: "tê",
    U: "u",
    Ư: "ư",
    V: "vê",
    X: "ích xì",
    Y: "i dài",
  };
  const sayName = (letter) =>
    lang === "en" ? letter : viNames[letter] || letter;
  UI.stage.innerHTML =
    '<div class="game-panel"><span class="eyebrow">' +
    (lang === "en" ? "ENGLISH ALPHABET" : "BẢNG CHỮ CÁI TIẾNG VIỆT") +
    '</span><h2 id="alphabetGuide">Chạm vào chữ để nghe</h2><button id="readAlphabet" class="primary-button">🔊 Đọc toàn bộ bảng chữ cái</button><div class="alphabet-grid">' +
    letters.map((x) => '<button class="letter">' + x + "</button>").join("") +
    "</div></div>";
  const buttons = $$(".letter");
  const heard = new Set(),
    epoch = gameEpoch;
  buttons.forEach(
    (b) =>
      (b.onclick = () => {
        speak(sayName(b.textContent), lang === "en" ? "en-US" : "vi-VN");
        if (!heard.has(b.textContent)) {
          heard.add(b.textContent);
          b.classList.add("learned");
          reward(2, "Đã khám phá " + heard.size + " chữ");
        }
      }),
  );
  $("#readAlphabet").onclick = async () => {
    const readButton = $("#readAlphabet");
    readButton.disabled = true;
    buttons.forEach((b) => (b.disabled = true));
    for (let i = 0; i < buttons.length; i++) {
      buttons[i].classList.add("speaking");
      await speakAsync(sayName(letters[i]), lang === "en" ? "en-US" : "vi-VN");
      if (epoch !== gameEpoch) return;
      buttons[i].classList.remove("speaking");
    }
    buttons.forEach((b) => (b.disabled = false));
    readButton.disabled = false;
  };
  startTimer();
}
async function memoryGame() {
  const items = await getGameItems(profile().pairs),
    count = items.length,
    cards = shuffle(
      items.flatMap((x, i) => [
        { ...x, key: i },
        { ...x, key: i },
      ]),
    );
  let open = [],
    done = new Set();
  const draw = () => {
    UI.stage.innerHTML =
      '<div class="game-panel"><span class="eyebrow">TRÍ NHỚ HÌNH ẢNH</span><h2>Tìm các cặp giống nhau</h2><div class="memory-grid">' +
      cards
        .map(
          (x, i) =>
            '<button class="memory-card ' +
            (open.includes(i) ? "open" : "") +
            (done.has(x.key) ? " done" : "") +
            '" data-i="' +
            i +
            '">' +
            (open.includes(i) || done.has(x.key)
              ? '<img src="' +
                thumb(x.image) +
                '" alt="' +
                escapeHtml(x.viName) +
                '">'
              : "?") +
            "</button>",
        )
        .join("") +
      "</div></div>";
    $$(".memory-card:not(.done)").forEach(
      (b) =>
        (b.onclick = () => {
          const i = +b.dataset.i;
          if (open.includes(i) || open.length === 2) return;
          open.push(i);
          draw();
          if (open.length === 2)
            later(() => {
              if (cards[open[0]].key === cards[open[1]].key) {
                done.add(cards[open[0]].key);
                reward(20);
              } else miss("Hai hình chưa giống nhau");
              open = [];
              if (done.size === count)
                return finishGame(true, "Đã tìm đủ các cặp!");
              draw();
            }, 650);
        }),
    );
  };
  draw();
}
function bomberGame() {
  const size =
      State.setup.difficulty === "hard"
        ? 10
        : State.setup.difficulty === "normal"
          ? 8
          : 6,
    mineCount =
      State.setup.difficulty === "hard"
        ? 15
        : State.setup.difficulty === "normal"
          ? 9
          : 5,
    total = size * size;
  let mines = new Set(),
    open = new Set(),
    flags = new Set(),
    ended = false,
    markMode = false,
    started = false;
  const neighbours = (i) => {
    const r = Math.floor(i / size),
      c = i % size,
      out = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        const nr = r + dr,
          nc = c + dc;
        if ((dr || dc) && nr >= 0 && nr < size && nc >= 0 && nc < size)
          out.push(nr * size + nc);
      }
    return out;
  };
  const count = (i) => neighbours(i).filter((n) => mines.has(n)).length;
  const reveal = (i) => {
    if (open.has(i) || flags.has(i) || ended) return;
    if (!started) {
      const safe = new Set([i, ...neighbours(i)]);
      mines = new Set(
        shuffle([...Array(total).keys()].filter((x) => !safe.has(x))).slice(
          0,
          mineCount,
        ),
      );
      started = true;
    }
    if (mines.has(i)) {
      ended = true;
      mines.forEach((x) => open.add(x));
      draw();
      later(
        () => finishGame(false, "Gặp ô đá rồi! Cùng xem lại các ô số nhé."),
        1000,
      );
      return;
    }
    const queue = [i];
    while (queue.length) {
      const x = queue.shift();
      if (open.has(x) || flags.has(x) || mines.has(x)) continue;
      open.add(x);
      if (count(x) === 0)
        neighbours(x).forEach((n) => {
          if (!open.has(n)) queue.push(n);
        });
    }
    if (open.size === total - mineCount) {
      ended = true;
      reward(100);
      draw();
      later(() => finishGame(true, "Khu vườn đã được khám phá!"), 700);
    } else draw();
  };
  const flag = (i) => {
    if (open.has(i) || ended) return;
    flags.has(i) ? flags.delete(i) : flags.add(i);
    draw();
  };
  const draw = () => {
    UI.stage.innerHTML =
      '<div class="game-panel mines-panel"><span class="eyebrow">KHU VƯỜN Ô SỐ</span><h2>Mở ô an toàn, tránh các ô đá</h2><p class="instruction">' +
      mineCount +
      " ô đá · Đã đánh dấu " +
      flags.size +
      ' ô</p><button id="flagMode" class="secondary-button" aria-pressed="' +
      markMode +
      '">' +
      (markMode
        ? "🚩 Đang đánh dấu — chạm để chuyển sang mở ô"
        : "🌱 Đang mở ô — chạm để chuyển sang đánh dấu") +
      '</button><div class="mines-grid" style="--mine-size:' +
      size +
      '">' +
      [...Array(total).keys()]
        .map((i) => {
          const n = count(i),
            opened = open.has(i);
          return (
            '<button aria-label="Hàng ' +
            (Math.floor(i / size) + 1) +
            " cột " +
            ((i % size) + 1) +
            (opened
              ? mines.has(i)
                ? ": ô đá"
                : ": " + n + " ô đá xung quanh"
              : flags.has(i)
                ? ": đã đánh dấu"
                : ": chưa mở") +
            '" class="mine-cell ' +
            (opened ? "open" : "") +
            '" data-mine-cell="' +
            i +
            '">' +
            (opened
              ? mines.has(i)
                ? "🪨"
                : n || "·"
              : flags.has(i)
                ? "🚩"
                : "") +
            "</button>"
          );
        })
        .join("") +
      '</div><p class="instruction">Số trên ô cho biết số ô đá ở 8 ô xung quanh. Lượt mở đầu luôn an toàn.</p></div>';
    $("#flagMode").onclick = () => {
      markMode = !markMode;
      draw();
    };
    $$("[data-mine-cell]").forEach((b) => {
      const i = +b.dataset.mineCell;
      b.onclick = () => (markMode ? flag(i) : reveal(i));
      b.oncontextmenu = (e) => {
        e.preventDefault();
        flag(i);
      };
    });
  };
  draw();
}
async function hiddenObjectGame() {
  const epoch = gameEpoch;
  const topics = await Promise.all(
      ["animal", "transport", "plant", "object"].map(topicData),
    ),
    transparent = (x) => /imagegen-v86/i.test(x.image || ""),
    transparentPool = topics.flatMap(validItems).filter(transparent),
    library = shuffle(
      transparentPool.length ? transparentPool : topics.flatMap(validItems),
    ).slice(0, 80),
    level = 1 + Math.floor(Math.random() * 30),
    target = library[level % library.length],
    scene = State.hiddenScenes[(level - 1) % State.hiddenScenes.length],
    required =
      State.setup.difficulty === "hard"
        ? 8
        : State.setup.difficulty === "normal"
          ? 6
          : 4;
  abortOld(epoch);
  if (!target) throw Error("Chủ đề chưa có ảnh");
  if (!scene) throw Error("Bộ 30 ảnh nền tìm vật chưa tải được");
  const positions = shuffle([
    [5, 10],
    [18, 35],
    [32, 8],
    [44, 45],
    [58, 17],
    [72, 38],
    [84, 9],
    [10, 68],
    [29, 64],
    [51, 70],
    [68, 63],
    [84, 70],
  ])
    .slice(0, required)
    .map(([x, y], i) => [
      x,
      y,
      (profile().id === "preschool" ? 64 : 44) + ((level * 7 + i * 11) % 25),
      -14 + ((level * 5 + i * 9) % 28),
    ]);
  UI.stage.innerHTML =
    '<div class="game-panel hidden-panel"><div class="hidden-targets"><span>Màn ' +
    level +
    "/30 · " +
    escapeHtml(scene.viName) +
    '</span><span><img src="' +
    asset(target.image) +
    '" alt="' +
    escapeHtml(target.viName) +
    '"> ' +
    escapeHtml(target.viName) +
    ' × <b id="hiddenRemaining">' +
    required +
    '</b></span></div><div class="hidden-scene themed-scene"><img class="hidden-scene-background" src="' +
    scene.image +
    '" alt="' +
    escapeHtml(scene.viName) +
    '">' +
    positions
      .map(
        (p, i) =>
          '<button class="hidden-object" aria-label="' +
          escapeHtml(target.viName) +
          " ẩn số " +
          (i + 1) +
          '" data-hidden="' +
          i +
          '" style="left:' +
          p[0] +
          "%;top:" +
          p[1] +
          "%;width:" +
          p[2] +
          "px;transform:rotate(" +
          p[3] +
          "deg);opacity:" +
          (0.58 + (i % 3) * 0.13) +
          '"><img src="' +
          asset(target.image) +
          '" alt=""></button>',
      )
      .join("") +
    "</div></div>";
  AudioSystem.startMusic();
  let found = 0;
  $$("[data-hidden]").forEach(
    (b) =>
      (b.onclick = () => {
        if (b.disabled) return;
        b.disabled = true;
        b.classList.add("found");
        AudioSystem.effect("found");
        reward(25, "Đã tìm thấy " + target.viName);
        $("#hiddenRemaining").textContent = required - ++found;
        if (found === required) {
          AudioSystem.effect("success");
          later(
            () =>
              finishGame(
                true,
                "Đã tìm đủ " + required + " " + target.viName + "!",
              ),
            500,
          );
        }
      }),
  );
}
function ticTacToe() {
  const size =
      State.setup.difficulty === "hard"
        ? 7
        : State.setup.difficulty === "normal"
          ? 5
          : 3,
    target = size === 3 ? 3 : 4,
    marks = Array(size * size).fill("");
  let player = "X",
    ended = false;
  UI.stage.innerHTML =
    '<div class="game-panel"><span class="eyebrow">HAI NGƯỜI · NỐI ' +
    target +
    ' QUÂN</span><h2 id="caroTurn">Lượt của bạn X</h2><p class="instruction">Nối ' +
    target +
    ' quân ngang, dọc hoặc chéo. Hai bạn thay phiên nhau.</p><div class="caro-grid" style="--size:' +
    size +
    '">' +
    marks
      .map(
        (_, i) =>
          '<button data-caro="' +
          i +
          '" aria-label="Hàng ' +
          (Math.floor(i / size) + 1) +
          " cột " +
          ((i % size) + 1) +
          ' trống"></button>',
      )
      .join("") +
    "</div></div>";
  $$("[data-caro]").forEach(
    (b) =>
      (b.onclick = () => {
        const i = +b.dataset.caro;
        if (ended || marks[i]) return;
        marks[i] = player;
        b.textContent = player;
        b.disabled = true;
        b.setAttribute(
          "aria-label",
          b.getAttribute("aria-label").replace("trống", player),
        );
        const r = Math.floor(i / size),
          c = i % size;
        const line = (dr, dc) => {
          let n = 0;
          for (let k = 1; k < size; k++) {
            const rr = r + dr * k,
              cc = c + dc * k;
            if (
              rr < 0 ||
              rr >= size ||
              cc < 0 ||
              cc >= size ||
              marks[rr * size + cc] !== player
            )
              break;
            n++;
          }
          return n;
        };
        if (
          [
            [1, 0],
            [0, 1],
            [1, 1],
            [1, -1],
          ].some(([dr, dc]) => 1 + line(dr, dc) + line(-dr, -dc) >= target)
        ) {
          ended = true;
          reward(50);
          later(
            () =>
              finishGame(
                true,
                "Bạn " + player + " đã nối đủ " + target + " quân!",
              ),
            700,
          );
        } else if (marks.every(Boolean)) {
          ended = true;
          later(
            () => finishGame(true, "Hai bạn hòa! Cùng chia sẻ chiến lược nhé."),
            600,
          );
        } else {
          player = player === "X" ? "O" : "X";
          $("#caroTurn").textContent = "Lượt của bạn " + player;
        }
      }),
  );
}
function colorGame() {
  const colors = [
    ["Đỏ", "#d73333"],
    ["Cam", "#e97a00"],
    ["Vàng", "#f4ce26"],
    ["Xanh lá", "#338547"],
    ["Xanh dương", "#247ed1"],
    ["Tím", "#8355a8"],
    ["Hồng", "#e578ab"],
    ["Nâu", "#795548"],
    ["Đen", "#202124"],
    ["Trắng", "#ffffff"],
  ];
  let round = 0;
  const draw = () => {
    if (round >= 6) return finishGame(true, "Đã khám phá những màu thật đẹp!");
    let answered = false;
    const options = shuffle(colors).slice(
        0,
        profile().id === "preschool" ? 3 : 6,
      ),
      target = options[Math.floor(Math.random() * options.length)];
    UI.stage.innerHTML =
      '<div class="game-panel color-lab"><span class="eyebrow">CÂU ' +
      (round + 1) +
      " / 6</span><h2>Tìm màu " +
      target[0] +
      '</h2><div class="color-sample" style="background:' +
      target[1] +
      '" role="img" aria-label="Màu ' +
      target[0] +
      '"></div><button id="hearColor" class="primary-button">🔊 Nghe tên màu</button><div class="color-grid">' +
      options
        .map(
          (c) =>
            '<button class="color-card" data-name="' +
            c[0] +
            '"><span class="color-paint" style="background:' +
            c[1] +
            '"></span><b>' +
            c[0] +
            "</b></button>",
        )
        .join("") +
      "</div></div>";
    $("#hearColor").onclick = () => speak(target[0]);
    $$(".color-card").forEach(
      (b) =>
        (b.onclick = () => {
          if (answered) return;
          if (b.dataset.name === target[0]) {
            answered = true;
            b.classList.add("correct");
            reward(15);
            round++;
            later(draw, 700);
          } else miss("Nhìn lại màu mẫu rồi thử nhé!");
        }),
    );
  };
  draw();
}
function mathGame(advanced) {
  let round = 0;
  const next = () => {
    if (round >= 6) return finishGame(true, "Đã hoàn thành lượt luyện toán!");
    let answered = false;
    const limit = profile().limit;
    let a, b, answer, op, hint;
    if (advanced) {
      const cap =
        State.setup.difficulty === "easy"
          ? 5
          : State.setup.difficulty === "hard"
            ? 12
            : 9;
      a = 1 + Math.floor(Math.random() * cap);
      b = 1 + Math.floor(Math.random() * cap);
      op = round % 2 ? "×" : "÷";
      if (op === "×") {
        answer = a * b;
        hint =
          a +
          " nhóm, mỗi nhóm " +
          b +
          " vật. Cộng " +
          b +
          " với chính nó " +
          a +
          " lần.";
      } else {
        answer = a;
        a *= b;
        hint =
          "Chia " + a + " vật thành các nhóm " + b + " vật. Có bao nhiêu nhóm?";
      }
    } else {
      a = 1 + Math.floor(Math.random() * limit);
      b = Math.floor(Math.random() * (limit - a + 1));
      op = round % 2 ? "+" : "−";
      if (op === "+") {
        answer = a + b;
        hint = "Có " + a + " vật, thêm " + b + " vật. Đếm tất cả.";
      } else {
        a = Math.max(a, b);
        b = Math.floor(Math.random() * (a + 1));
        answer = a - b;
        hint = "Có " + a + " vật, bớt " + b + " vật. Còn bao nhiêu?";
      }
    }
    const q = a + " " + op + " " + b,
      answers = numberChoices(answer, profile().choices);
    UI.stage.innerHTML =
      '<div class="game-panel"><span class="eyebrow">CÂU ' +
      (round + 1) +
      ' / 6</span><h2 class="math-question">' +
      q +
      ' = ?</h2><div class="controls"><button id="hearMath" class="secondary-button">🔊 Nghe câu hỏi</button><button id="mathHint" class="secondary-button">💡 Gợi ý</button></div><p id="mathHintText" class="math-hint" hidden>' +
      escapeHtml(hint) +
      (!advanced && a <= 20
        ? '<span class="math-dots">' + Array(a).fill("●").join(" ") + "</span>"
        : "") +
      '</p><div class="answer-grid">' +
      answers.map((x) => '<button class="answer">' + x + "</button>").join("") +
      "</div></div>";
    $("#hearMath").onclick = () =>
      speak(
        a +
          " " +
          { "+": "cộng", "−": "trừ", "×": "nhân", "÷": "chia" }[op] +
          " " +
          b +
          " bằng bao nhiêu?",
      );
    $("#mathHint").onclick = () => {
      $("#mathHintText").hidden = false;
      speak(hint);
    };
    $$(".answer").forEach(
      (x, i) =>
        (x.onclick = () => {
          if (answered) return;
          if (answers[i] === answer) {
            answered = true;
            x.classList.add("correct");
            reward(20);
            round++;
            later(next, 700);
          } else {
            miss("Thử dùng gợi ý để kiểm tra nhé!");
            $("#mathHintText").hidden = false;
          }
        }),
    );
  };
  next();
}
async function matchGame(type) {
  const epoch = gameEpoch;
  const isTransport = type === "transport",
    pool = validItems(
      await topicData(isTransport ? "transport" : "animal"),
    ).sort(
      (a, b) =>
        Number(String(b.id || "").startsWith("pack-v82")) -
        Number(String(a.id || "").startsWith("pack-v82")),
    ),
    used = new Set();
  abortOld(epoch);
  const specs = isTransport
    ? [
        {
          key: "road",
          find: /xe đạp|ô tô|xe hơi|xe buýt|mô tô|bicycle|car|bus|motor/i,
          image: "transport-mode-road-v83.png",
        },
        {
          key: "waterway",
          find: /ca nô|canoe|phà|ferry/i,
          image: "transport-mode-waterway-v83.png",
        },
        {
          key: "aviation",
          find: /máy bay|trực thăng|airplane|helicopter/i,
          image: "transport-mode-aviation-v83.png",
        },
        {
          key: "rail",
          find: /tàu hỏa|xe lửa|train|tram/i,
          image: "transport-mode-rail-v83.png",
        },
        {
          key: "maritime",
          find: /tàu thủy|tàu biển|thuyền buồm|ship|sailboat/i,
          image: "transport-mode-maritime-v83.png",
        },
      ]
    : [
        {
          key: "ocean",
          find: /cá heo mũi chai|common bottlenose dolphin/i,
          image: "environment-ocean-v83.png",
        },
        {
          key: "farmland",
          find: /con bò|bò$|cow/i,
          image: "environment-farmland-v83.png",
        },
        {
          key: "forest",
          find: /hổ đông dương|indochinese tiger/i,
          image: "environment-forest-v83.png",
        },
        {
          key: "grassland",
          find: /sư tử châu phi|african lion/i,
          image: "environment-grassland-v83.png",
        },
        {
          key: "snow",
          find: /gấu bắc cực|polar bear/i,
          image: "environment-snow-mountain-v83.png",
        },
        { key: "river", find: /vịt|duck/i, image: "environment-river-v83.png" },
        {
          key: "countryside",
          find: /chó|dog/i,
          image: "environment-countryside-v83.png",
        },
        {
          key: "maple",
          find: /bướm|butterfly/i,
          image: "environment-maple-forest-v83.png",
        },
      ];
  const targetNames = {
    road: "Đường bộ",
    waterway: "Sông, kênh",
    aviation: "Hàng không",
    rail: "Đường sắt",
    maritime: "Biển",
    military: "Quân sự",
    "road-heavy": "Đường bộ",
    "space-flight": "Không gian",
    ocean: "Đại dương",
    farmland: "Nông trại",
    forest: "Rừng",
    grassland: "Đồng cỏ",
    snow: "Vùng băng tuyết",
    river: "Sông, hồ",
    countryside: "Khu dân cư",
    maple: "Rừng",
  };
  const pairCount =
      State.setup.difficulty === "hard"
        ? 8
        : State.setup.difficulty === "normal"
          ? 6
          : 4,
    activeSpecs = specs.slice(0, pairCount),
    entries = activeSpecs
      .map((s, i) => {
        let item = pool.find(
            (x, n) => !used.has(n) && s.find.test(x.viName + " " + x.enName),
          ),
          idx = item ? pool.indexOf(item) : -1;
        if (!item) return null;
        used.add(idx);
        return { ...s, item };
      })
      .filter(Boolean),
    left = shuffle(entries),
    right = shuffle(entries);
  if (entries.length < 2) throw Error("Chưa đủ cặp hình phù hợp");
  let selected = null,
    done = 0;
  UI.stage.innerHTML =
    '<div class="game-panel"><span class="eyebrow">KÉO ẢNH ĐỂ NỐI</span><h2>' +
    (isTransport
      ? "Đưa phương tiện vào đúng môi trường di chuyển"
      : "Đưa con vật vào đúng môi trường sống") +
    '</h2><div class="visual-match-board" id="visualMatchBoard"><svg class="match-lines" id="matchLines"></svg><div class="match-column source-column">' +
    left
      .map(
        (x, i) =>
          '<button class="visual-match-item" draggable="true" aria-label="' +
          escapeHtml(x.item.viName) +
          '" data-source="' +
          i +
          '"><img src="' +
          thumb(x.item.image) +
          '" alt=""></button>',
      )
      .join("") +
    '</div><div class="match-column target-column">' +
    right
      .map(
        (x, i) =>
          '<button class="visual-match-target" aria-label="' +
          targetNames[x.key] +
          '" data-target-key="' +
          x.key +
          '"><img src="' +
          asset("images/transparent-library/" + x.image) +
          '" alt=""><b>' +
          targetNames[x.key] +
          "</b></button>",
      )
      .join("") +
    '</div></div><p class="instruction">Chạm một hình bên trái, rồi chạm môi trường phù hợp bên phải. Cũng có thể kéo thả.</p></div>';
  const lines = [];
  const drawLines = () => {
    const board = $("#visualMatchBoard"),
      svg = $("#matchLines");
    if (!board || !svg) return;
    const br = board.getBoundingClientRect();
    svg.setAttribute("viewBox", "0 0 " + br.width + " " + br.height);
    svg.innerHTML = lines
      .map((x) => {
        const a = x.source.getBoundingClientRect(),
          b = x.target.getBoundingClientRect();
        return (
          '<line x1="' +
          (a.right - br.left) +
          '" y1="' +
          (a.top + a.height / 2 - br.top) +
          '" x2="' +
          (b.left - br.left) +
          '" y2="' +
          (b.top + b.height / 2 - br.top) +
          '" />'
        );
      })
      .join("");
  };
  const connect = (sourceIndex, target) => {
    const source = $('[data-source="' + sourceIndex + '"]'),
      entry = left[sourceIndex];
    if (!source || source.classList.contains("done")) return;
    if (entry.key !== target.dataset.targetKey) {
      target.classList.add("wrong");
      later(() => target.classList.remove("wrong"), 400);
      return miss("Hình này chưa đúng môi trường");
    }
    source.classList.add("done");
    target.classList.add("connected");
    lines.push({ source, target });
    drawLines();
    reward(30, "Nối đúng!");
    selected = null;
    if (++done === entries.length)
      later(() => finishGame(true, "Đã nối đúng tất cả hình ảnh!"), 500);
  };
  $$("[data-source]").forEach((b) => {
    b.ondragstart = (e) => {
      e.dataTransfer.setData("text/plain", b.dataset.source);
      e.dataTransfer.effectAllowed = "move";
    };
    b.onclick = () => {
      selected = +b.dataset.source;
      $$("[data-source]").forEach((x) =>
        x.classList.toggle("selected", x === b),
      );
    };
  });
  $$("[data-target-key]").forEach((b) => {
    b.ondragover = (e) => {
      e.preventDefault();
      b.classList.add("dragover");
    };
    b.ondragleave = () => b.classList.remove("dragover");
    b.ondrop = (e) => {
      e.preventDefault();
      b.classList.remove("dragover");
      connect(+e.dataTransfer.getData("text/plain"), b);
    };
    b.onclick = () => {
      if (selected !== null) connect(selected, b);
    };
  });
  addEventListener("resize", drawLines);
  State.cleanup = () => removeEventListener("resize", drawLines);
}
function spaceShooter() {
  UI.stage.innerHTML =
    '<div class="game-panel"><span class="eyebrow">DU HÀNH VŨ TRỤ · 3 TIM</span><h2>Lái tàu, tránh thiên thạch, đón ngôi sao</h2><canvas id="spaceCanvas" class="space-canvas" width="900" height="540"></canvas><div class="controls"><button data-move="-1">←</button><button data-move="up">↑</button><span class="auto-fire-label">TỰ ĐỘNG BẮN · ĐỘ KHÓ TĂNG DẦN</span><button data-move="down">↓</button><button data-move="1">→</button></div></div>';
  const cv = $("#spaceCanvas"),
    ctx = cv.getContext("2d"),
    ship = { x: 450, y: 490 },
    shots = [],
    rocks = [],
    drops = [];
  let running = true,
    beams = 1,
    angle = 0,
    shipLevel = 1,
    xp = 0,
    hearts = 3,
    ticks = 0,
    invincible = 0;
  const move = (dx, dy = 0) => {
      ship.x = Math.max(28, Math.min(872, ship.x + dx * 36));
      ship.y = Math.max(290, Math.min(510, ship.y + dy * 30));
    },
    fire = () => {
      const n = Math.min(5, beams),
        maxAngle = (Math.min(45, angle) * Math.PI) / 180;
      AudioSystem.effect("shot");
      for (let i = 0; i < n; i++) {
        const a = n === 1 ? 0 : -maxAngle / 2 + (maxAngle * i) / (n - 1);
        shots.push({
          x: ship.x,
          y: ship.y - 28,
          vx: Math.sin(a) * (10 + shipLevel * 0.35),
          vy: -Math.cos(a) * (10 + shipLevel * 0.35),
          power: 1 + Math.floor((shipLevel - 1) / 3),
        });
      }
    };
  $$("[data-move]").forEach(
    (b) =>
      (b.onclick = () =>
        b.dataset.move === "up"
          ? move(0, -1)
          : b.dataset.move === "down"
            ? move(0, 1)
            : move(+b.dataset.move)),
  );
  const key = (e) => {
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key))
      e.preventDefault();
    if (e.key === "ArrowLeft" || e.key === "a") move(-1);
    if (e.key === "ArrowRight" || e.key === "d") move(1);
    if (e.key === "ArrowUp" || e.key === "w") move(0, -1);
    if (e.key === "ArrowDown" || e.key === "s") move(0, 1);
  };
  addEventListener("keydown", key);
  cv.onpointermove = (e) => {
    if (e.buttons || e.pointerType === "touch") {
      const r = cv.getBoundingClientRect();
      ship.x = Math.max(
        28,
        Math.min(872, ((e.clientX - r.left) * 900) / r.width),
      );
      ship.y = Math.max(
        290,
        Math.min(510, ((e.clientY - r.top) * 540) / r.height),
      );
    }
  };
  const collect = (d) => {
    d.dead = true;
    if (d.type === "beam") {
      beams = Math.min(5, beams + 1);
      reward(25, "Tăng lên " + beams + " tia đạn");
    } else if (d.type === "angle") {
      angle = Math.min(45, angle + 9);
      reward(25, "Góc bắn " + angle + "°");
    } else {
      xp += 2;
      while (xp >= 5 && shipLevel < 10) {
        xp -= 5;
        shipLevel++;
        reward(50, "Phi thuyền lên cấp " + shipLevel);
      }
    }
  };
  const damage = (message) => {
      if (invincible || !running) return;
      AudioSystem.effect("damage");
      hearts--;
      invincible = 75;
      showToast(message + " · Còn " + hearts + " tim");
      if (hearts <= 0) explode();
    },
    explode = () => {
      running = false;
      for (let i = 0; i < 24; i++) {
        ctx.fillStyle = i % 2 ? "#ffcf5a" : "#ff624d";
        ctx.beginPath();
        ctx.arc(
          ship.x + (Math.random() - 0.5) * 130,
          ship.y + (Math.random() - 0.5) * 100,
          7 + Math.random() * 22,
          0,
          Math.PI * 2,
        );
        ctx.fill();
      }
      later(
        () =>
          finishGame(
            false,
            "Hết lượt bay! Nghỉ tay rồi cùng kể về chuyến đi nhé.",
          ),
        650,
      );
    };
  const drawMeteor = (r) => {
    ctx.save();
    ctx.translate(r.x, r.y);
    ctx.rotate(r.spin);
    const g = ctx.createRadialGradient(-r.r * 0.28, -r.r * 0.32, 2, 0, 0, r.r);
    g.addColorStop(
      0,
      ["#d7a06f", "#b78a67", "#9f8d82", "#8d6a62", "#7c7087"][r.kind % 5],
    );
    g.addColorStop(1, "#30252a");
    ctx.fillStyle = g;
    ctx.strokeStyle = "#e4b17a88";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < 12; i++) {
      const a = (i * Math.PI) / 6,
        rr = r.r * (0.82 + 0.18 * Math.sin(i * 4.7 + r.seed));
      i
        ? ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr)
        : ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#241b2088";
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.ellipse(
        (i - 1) * r.r * 0.28,
        ((i % 2) - 0.5) * r.r * 0.38,
        r.r * (0.1 + i * 0.025),
        r.r * (0.07 + i * 0.02),
        i,
        0,
        Math.PI * 2,
      );
      ctx.fill();
    }
    ctx.restore();
  };
  const drawShip = () => {
    ctx.save();
    ctx.translate(ship.x, ship.y);
    const s = 1 + shipLevel * 0.035;
    ctx.scale(s, s);
    ctx.globalAlpha = invincible && ticks % 8 < 4 ? 0.3 : 1;
    ctx.shadowColor = shipLevel > 6 ? "#c594ff" : "#52e9ff";
    ctx.shadowBlur = 10 + shipLevel * 2;
    ctx.fillStyle = shipLevel > 6 ? "#7a63d8" : "#178ca7";
    ctx.strokeStyle = "#e8fbff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, -34 - shipLevel);
    ctx.lineTo(19, -4);
    ctx.lineTo(14, 23);
    ctx.lineTo(0, 14);
    ctx.lineTo(-14, 23);
    ctx.lineTo(-19, -4);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    if (shipLevel >= 3) {
      ctx.fillStyle = "#3559a8";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(side * 14, 4);
        ctx.lineTo(side * (32 + shipLevel), 20);
        ctx.lineTo(side * 13, 17);
        ctx.closePath();
        ctx.fill();
      }
    }
    if (shipLevel >= 6) {
      ctx.fillStyle = "#ffd166";
      ctx.fillRect(-30, 10, 7, 18);
      ctx.fillRect(23, 10, 7, 18);
    }
    if (shipLevel >= 9) {
      ctx.strokeStyle = "#bda7ff";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(0, 0, 43, Math.PI * 0.15, Math.PI * 0.85, true);
      ctx.stroke();
    }
    ctx.fillStyle = "#d8ffff";
    ctx.beginPath();
    ctx.ellipse(0, -7, 6, 10, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ff8a45";
    ctx.beginPath();
    ctx.moveTo(-7, 22);
    ctx.lineTo(0, 39 + Math.random() * 8);
    ctx.lineTo(7, 22);
    ctx.fill();
    ctx.restore();
  };
  const frame = () => {
    if (!running) return;
    ticks++;
    invincible = Math.max(0, invincible - 1);
    const wave = 1 + Math.floor(ticks / 900),
      spawnEvery = Math.max(13, 40 - wave * 2);
    if (ticks % Math.max(8, 14 - Math.floor(shipLevel / 4)) === 0) fire();
    if (ticks % spawnEvery === 0) {
      const kind = Math.floor(Math.random() * 10),
        r = 13 + kind * 3.6,
        hp = Math.min(4, 1 + Math.floor(kind / 3) + Math.floor(wave / 5));
      rocks.push({
        x: 30 + Math.random() * 840,
        y: -45,
        r,
        v: 1.25 + Math.random() * 1.4 + wave * 0.13,
        hp,
        maxHp: hp,
        kind,
        spin: 0,
        seed: Math.random() * 9,
      });
    }
    shots.forEach((s) => {
      s.x += s.vx;
      s.y += s.vy;
    });
    rocks.forEach((r) => {
      r.y += r.v;
      r.spin += 0.006 + r.kind * 0.001;
    });
    drops.forEach((d) => (d.y += 2.2));
    for (const s of shots)
      for (const r of rocks)
        if (!s.dead && !r.dead && Math.hypot(s.x - r.x, s.y - r.y) < r.r + 5) {
          s.dead = true;
          r.hp -= s.power;
          AudioSystem.effect("meteor");
          if (r.hp <= 0) {
            r.dead = true;
            reward(10 + 5 * r.maxHp, "Phá thiên thạch");
            xp++;
            while (xp >= 5 && shipLevel < 10) {
              xp -= 5;
              shipLevel++;
              showToast("Phi thuyền lên cấp " + shipLevel);
            }
            if (Math.random() < 0.3)
              drops.push({
                x: r.x,
                y: r.y,
                type: ["beam", "angle", "level"][Math.floor(Math.random() * 3)],
              });
          }
        }
    for (const d of drops)
      if (!d.dead && Math.hypot(d.x - ship.x, d.y - ship.y) < 38) collect(d);
    for (const r of rocks)
      if (!r.dead && Math.hypot(r.x - ship.x, r.y - ship.y) < r.r + 24) {
        r.dead = true;
        damage("Va chạm thiên thạch");
      }
    for (const r of rocks)
      if (!r.dead && r.y - r.r > 540)
        r.dead = true; /* Thiên thạch hoặc đạn đi trượt chỉ rời màn hình; tuyệt đối không trừ máu. */
    shots.splice(
      0,
      shots.length,
      ...shots.filter((s) => !s.dead && s.y > -30 && s.x > -20 && s.x < 920),
    );
    rocks.splice(0, rocks.length, ...rocks.filter((r) => !r.dead));
    drops.splice(0, drops.length, ...drops.filter((d) => !d.dead && d.y < 570));
    ctx.clearRect(0, 0, 900, 540);
    ctx.fillStyle = "#020914";
    ctx.fillRect(0, 0, 900, 540);
    ctx.fillStyle = "rgba(93,225,219,.035)";
    ctx.fillRect(0, 270, 900, 270);
    ctx.fillStyle = "#fff";
    for (let i = 0; i < 80; i++)
      ctx.fillRect((i * 83) % 900, (i * 47 + ticks * 0.15) % 540, 1.5, 1.5);
    drawShip();
    shots.forEach((s) => {
      const g = ctx.createLinearGradient(s.x, s.y, s.x, s.y + 20);
      g.addColorStop(0, shipLevel > 6 ? "#fff" : "#5de1db");
      g.addColorStop(1, shipLevel > 3 ? "#9b8cff" : "#168ca5");
      ctx.fillStyle = g;
      ctx.shadowColor = shipLevel > 5 ? "#bf93ff" : "#4ef6ff";
      ctx.shadowBlur = 8 + shipLevel;
      ctx.fillRect(s.x - 2 - shipLevel / 5, s.y, 4 + shipLevel / 2, 20);
      ctx.shadowBlur = 0;
    });
    rocks.forEach(drawMeteor);
    drops.forEach((d) => {
      ctx.save();
      ctx.translate(d.x, d.y);
      ctx.fillStyle =
        d.type === "beam"
          ? "#55e9ff"
          : d.type === "angle"
            ? "#ffd166"
            : "#b98cff";
      ctx.rotate(ticks * 0.03);
      ctx.beginPath();
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4,
          rr = i % 2 ? 8 : 17;
        ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    });
    ctx.fillStyle = "#fff";
    ctx.font = "bold 15px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(
      "TIM " +
        hearts +
        "  ·  TIA " +
        beams +
        "  ·  GÓC " +
        angle +
        "°  ·  CẤP " +
        shipLevel +
        "/10  ·  ĐỘ KHÓ " +
        wave,
      20,
      28,
    );
    requestAnimationFrame(frame);
  };
  State.cleanup = () => {
    running = false;
    removeEventListener("keydown", key);
  };
  frame();
}

function renderTopics() {
  UI.topics.innerHTML = "";
  State.bootstrap.topics.forEach((t, i) => {
    const b = document.createElement("button");
    b.className = "topic-button" + (i === 0 ? " active" : "");
    b.dataset.topic = t.id;
    b.innerHTML = (TOPIC_ICONS[t.id] || "✦") + " " + escapeHtml(t.name.vi);
    b.onclick = () => loadTopic(t.id);
    UI.topics.appendChild(b);
  });
}
async function loadTopic(id) {
  State.topic = id;
  State.visible = 30;
  $$(".topic-button").forEach((b) =>
    b.classList.toggle("active", b.dataset.topic === id),
  );
  UI.libraryGrid.innerHTML = '<div class="result-box">Đang mở thư viện…</div>';
  try {
    const data=await topicData(id);if(State.topic!==id)return;State.items=validItems(data);
    renderLibrary();
  } catch (error) {
    UI.libraryGrid.innerHTML =
      '<div class="result-box"><h2>Chưa tải được thư viện</h2><p>' +
      escapeHtml(error.message) +
      "</p></div>";
  }
}
function filteredItems() {
  const q = (UI.search.value || "").toLocaleLowerCase("vi").trim();
  return q
    ? State.items.filter((x) =>
        (x.viName + " " + x.enName + " " + (x.description || ""))
          .toLocaleLowerCase("vi")
          .includes(q),
      )
    : State.items;
}
function renderLibrary() {
  const items = filteredItems(),
    topic = State.bootstrap.topics.find((t) => t.id === State.topic);
  $("#librarySummary").textContent =
    items.length + " mục trong " + (topic?.name.vi || "thư viện");
  UI.libraryGrid.innerHTML = "";
  items.slice(0, State.visible).forEach((x, i) => {
    const card = document.createElement("article");
    card.className = "library-card";
    card.innerHTML =
      '<button class="library-card-open" aria-label="Xem thông tin ' +
      escapeHtml(x.viName) +
      '"><span class="library-card-image"><span class="image-spark">✦</span><img loading="' +
      (i < 10 ? "eager" : "lazy") +
      '" src="' +
      thumb(x.image) +
      '" alt="' +
      escapeHtml(x.viName) +
      '"></span><span class="library-card-copy"><small>' +
      escapeHtml((topic?.name.vi || "THƯ VIỆN").toUpperCase()) +
      "</small><b>" +
      escapeHtml(x.viName) +
      "</b><em>" +
      escapeHtml(x.enName) +
      '</em><span class="discover-label">Khám phá <i>→</i></span></span></button><div class="library-card-audio"><button class="card-speak vi" aria-label="Đọc thông tin ' +
      escapeHtml(x.viName) +
      ' bằng tiếng Việt">🇻🇳 <span>Nghe VI</span></button><button class="card-speak en" aria-label="Read ' +
      escapeHtml(x.enName) +
      ' information in English">🇬🇧 <span>Listen EN</span></button></div>';
    card.querySelector("img").onerror = (e) => {
      e.currentTarget.onerror = null;
      e.currentTarget.src = asset(x.image);
    };
    card.querySelector(".library-card-open").onclick = () => openDetail(x);
    card.querySelector(".card-speak.vi").onclick = () => speakItem(x, "vi");
    card.querySelector(".card-speak.en").onclick = () => speakItem(x, "en");
    UI.libraryGrid.appendChild(card);
  });
  $("#loadMore").hidden = State.visible >= items.length;
}
function openDetail(item) {
  State.detailItem = item;
  const topic = State.bootstrap.topics.find((t) => t.id === State.topic);
  $("#detailImage").src = asset(item.image);
  $("#detailImage").alt = item.viName;
  $("#detailTopic").textContent =
    (TOPIC_ICONS[State.topic] || "✦") + " " + (topic?.name.vi || "Thư viện");
  $("#detailName").textContent = item.viName;
  $("#detailEnglish").textContent = item.enName + " 🔊";
  $("#detailDescriptionVi").textContent = item.description || "";
  $("#detailDescriptionEn").textContent =
    item.descriptionEn || "English name: " + item.enName + ".";
  const facts = item.facts || [],
    shown = (
      facts.length
        ? facts
        : [
            {
              label: "Tiếng Việt",
              labelEn: "Vietnamese",
              value: item.viName,
              valueEn: item.enName,
            },
          ]
    ).slice(0, 6);
  $("#detailFacts").innerHTML = shown
    .map(
      (f, i) =>
        '<article class="fact-card"><header><span class="fact-icon">' +
        escapeHtml(factIcon(f)) +
        "</span><b>" +
        escapeHtml(f.label || "Thông tin") +
        "<small>" +
        escapeHtml(f.labelEn || "Information") +
        '</small></b><span class="fact-audio"><button data-fact="' +
        i +
        '" data-lang="vi" aria-label="Đọc ' +
        escapeHtml(f.label || "thông tin") +
        ' bằng tiếng Việt">🇻🇳 🔊</button><button data-fact="' +
        i +
        '" data-lang="en" aria-label="Read ' +
        escapeHtml(f.labelEn || "information") +
        ' in English">🇬🇧 🔊</button></span></header><p>' +
        escapeHtml(f.value || f.text || "") +
        "</p><em>" +
        escapeHtml(f.valueEn || "") +
        "</em></article>",
    )
    .join("");
  $$("#detailFacts [data-fact]").forEach(
    (button) =>
      (button.onclick = () => {
        const f = shown[Number(button.dataset.fact)],
          english = button.dataset.lang === "en";
        speak(
          (english ? f.labelEn : f.label) +
            ". " +
            (english ? f.valueEn : f.value),
          english ? "en-US" : "vi-VN",
        );
      }),
  );
  showModal(UI.detail);
}
function renderDesign() {
  $("#designGrid").innerHTML = Object.values(State.bootstrap.education.guides)
    .map(
      (g) =>
        '<article class="design-card"><span>' +
        g.icon +
        "</span><h3>" +
        escapeHtml(g.title) +
        "</h3><p>" +
        escapeHtml(g.goal) +
        "</p><ol>" +
        g.steps.map((x) => "<li>" + escapeHtml(x) + "</li>").join("") +
        "</ol><p><b>Cùng con:</b> " +
        escapeHtml(g.parent) +
        "</p></article>",
    )
    .join("");
}

init();
