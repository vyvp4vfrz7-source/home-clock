/* Cute visitors: little animations that pop up now and then, never blocking a tap.
   - On the hour: the sleepy cat wakes and stretches, or the cuckoo pops out.
   - Every few minutes (CONFIG.cute.every, minutes): a random visitor that fits today.
   - Triggered: duck with umbrella when rain starts, snowman when it turns cold, a goal party when
     Man United score, birthday balloons, 中秋 lanterns, New Year / CNY / Bonfire Night fireworks, winter snow.
   - At night: a dim little fish tank along the bottom of the night clock.
   Sounds go through sound.js (silent unless the speaker is turned up, never at night).
   Try one now with ?cute=cat|cuckoo|snow|lanterns|fireworks|duck|snowman|goal|balloons|all, fish with ?night=1. */
(function () {
  var C = window.Cute = { goal: function () {} };
  var cfg = (window.CONFIG && CONFIG.cute) || {};
  if (cfg.off) return;
  var EVERY = cfg.every || [6, 12];
  var body = document.body;
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
  function sfx(k) { if (window.HomeSound && HomeSound.chirp) HomeSound.chirp(k); }
  function later(fn, ms) { return setTimeout(fn, ms); }

  var css =
    '#cute{position:fixed;inset:0;z-index:45;pointer-events:none;overflow:hidden}' +
    '#cute *{pointer-events:none}' +
    '#cute .em{position:absolute;line-height:1;font-family:"Apple Color Emoji","Noto Color Emoji",sans-serif}' +
    '#cute .bub{position:absolute;background:#fff;color:#3a2a20;border-radius:14px;padding:4px 10px;font:600 15px/1.3 -apple-system,"PingFang HK",sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.2);white-space:nowrap;animation:cuPop .35s ease-out both}' +
    '@keyframes cuPop{from{transform:scale(0)}to{transform:scale(1)}}' +
    '@keyframes cuFade{to{opacity:0}}' +
    /* cat */
    '#cute .cat{position:absolute;width:130px;height:86px;transition:transform 5s linear}' +
    '#cute .cat svg{width:100%;height:100%;overflow:visible}' +
    '#cute .cat .open,#cute .cat.wake .shut{display:none}#cute .cat.wake .open{display:inline}' +
    '#cute .cat .bd{transform-origin:85px 70px;transform-box:view-box}' +
    '#cute .cat.stretch .bd{animation:cuStretch 2.2s ease-in-out}' +
    '@keyframes cuStretch{40%,60%{transform:scaleX(1.22) scaleY(.85)}}' +
    '#cute .cat .bth{transform-origin:50% 50%;transform-box:fill-box;animation:cuBreath 3s ease-in-out infinite}' +
    '@keyframes cuBreath{50%{transform:scaleY(1.06)}}' +
    '#cute .cat.walk svg{animation:cuBob .45s ease-in-out infinite alternate}' +
    '@keyframes cuBob{to{transform:translateY(-4px)}}' +
    '#cute .zz{position:absolute;font:700 18px sans-serif;color:#7d8fd8;animation:cuZ 3s ease-out infinite;opacity:0}' +
    '@keyframes cuZ{0%{opacity:0;transform:translate(0,0) scale(.6)}30%{opacity:1}100%{opacity:0;transform:translate(22px,-40px) scale(1.2)}}' +
    /* cuckoo */
    '#cute .cuk{position:absolute;width:96px;height:120px;transform-origin:50% 0;animation:cuDrop .6s ease-out both}' +
    '@keyframes cuDrop{from{transform:translateY(-130px)}to{transform:none}}' +
    '#cute .cuk.go{animation:cuUp .6s ease-in both}@keyframes cuUp{to{transform:translateY(-140px)}}' +
    '#cute .cuk .door{transform-origin:34px 60px;transform-box:view-box;transition:transform .4s}' +
    '#cute .cuk.open .door{transform:scaleX(.08)}' +
    '#cute .cuk .bird{transform:translateY(0);transition:transform .35s cubic-bezier(.3,1.6,.6,1)}' +
    '#cute .cuk.out .bird{transform:translateY(34px)}' +
    /* snow */
    '#cute .flake{position:absolute;top:-30px;color:#fff;text-shadow:0 0 4px rgba(120,150,200,.6);animation:cuFall linear both}' +
    '@keyframes cuFall{to{transform:translate(var(--dx),110vh) rotate(260deg)}}' +
    '#cute .cap{position:absolute;height:16px;transform-origin:50% 100%;transform:scaleY(0);animation:cuCap 16s ease-in-out both;' +
      'background:radial-gradient(circle at 10px 12px,#fff 9px,transparent 10px) 0 0/24px 16px repeat-x,linear-gradient(#fff,#fff) 0 10px/100% 6px no-repeat;filter:drop-shadow(0 2px 2px rgba(80,100,140,.35))}' +
    '@keyframes cuCap{0%{transform:scaleY(0)}70%{transform:scaleY(1)}88%{transform:scaleY(1);opacity:1}100%{transform:scaleY(.3);opacity:0}}' +
    /* rising things: lanterns, balloons */
    '#cute .rise{position:absolute;bottom:-90px;animation:cuRise linear both}' +
    '@keyframes cuRise{to{transform:translateY(calc(-100vh - 140px))}}' +
    '#cute .sway{display:block;animation:cuSway 3s ease-in-out infinite alternate}' +
    '@keyframes cuSway{from{transform:translateX(-14px) rotate(-6deg)}to{transform:translateX(14px) rotate(6deg)}}' +
    '#cute .glow{filter:drop-shadow(0 0 14px rgba(255,140,40,.8))}' +
    '#cute .banner{position:absolute;left:50%;top:16%;transform:translateX(-50%);background:rgba(255,255,255,.92);color:#c2185b;border-radius:22px;padding:10px 26px;font:700 30px/1.25 -apple-system,"PingFang HK",sans-serif;text-align:center;box-shadow:0 6px 20px rgba(0,0,0,.25);animation:cuPop .5s ease-out both}' +
    '#cute .banner small{display:block;font-size:17px;color:#7a4b5e;font-weight:600}' +
    /* walkers: duck, snowman */
    '#cute .walk{position:absolute;bottom:2.5vh;animation:cuWalk linear both}' +
    '@keyframes cuWalk{from{transform:translateX(-160px)}to{transform:translateX(calc(100vw + 160px))}}' +
    '#cute .waddle{display:block;animation:cuWad .4s ease-in-out infinite alternate}' +
    '@keyframes cuWad{from{transform:rotate(-7deg)}to{transform:rotate(7deg) translateY(-3px)}}' +
    '#cute .snowman{position:absolute;bottom:-150px;left:3vw;transition:transform 1.2s cubic-bezier(.3,1.4,.6,1)}' +
    '#cute .snowman.up{transform:translateY(-150px)}' +
    '#cute .snowman .em{position:relative;animation:cuWave 1s ease-in-out infinite alternate;transform-origin:50% 90%}' +
    '@keyframes cuWave{from{transform:rotate(-5deg)}to{transform:rotate(5deg)}}' +
    /* goal */
    '#cute .conf{position:absolute;top:-20px;width:10px;height:16px;border-radius:2px;animation:cuFall linear both}' +
    '#cute .dev{position:absolute;left:50%;bottom:-260px;width:220px;margin-left:-110px;transition:transform .7s cubic-bezier(.3,1.5,.6,1)}' +
    '#cute .dev.up{transform:translateY(-300px)}' +
    '#cute .dev svg{width:100%;animation:cuJump .5s ease-in-out infinite alternate}' +
    '@keyframes cuJump{to{transform:translateY(-18px) rotate(3deg)}}' +
    '#cute .gl{position:absolute;left:50%;top:22%;transform:translateX(-50%);font:900 72px/1 -apple-system,sans-serif;color:#fff;background:#da291c;padding:12px 34px;border-radius:24px;box-shadow:0 8px 30px rgba(0,0,0,.35);animation:cuPop .4s ease-out both}' +
    '#cute .gl small{display:block;font-size:26px;text-align:center;margin-top:6px;color:#fbe122}' +
    /* fish tank, inside the night screen */
    '#tank{position:absolute;left:0;right:0;bottom:0;height:22vh;overflow:hidden;opacity:.6;pointer-events:none;background:linear-gradient(rgba(10,40,80,0),rgba(10,40,80,.45))}' +
    '#tank .em{position:absolute;line-height:1;font-family:"Apple Color Emoji","Noto Color Emoji",sans-serif}' +
    '#tank .fish{left:100%;animation:cuSwim linear infinite}' +
    '@keyframes cuSwim{to{transform:translateX(calc(-100vw - 200px))}}' +
    '#tank .fish i{display:block;font-style:normal;animation:cuBobF 2.6s ease-in-out infinite alternate}' +
    '@keyframes cuBobF{to{transform:translateY(12px)}}' +
    '#tank .bubble{bottom:-12px;width:8px;height:8px;border-radius:50%;border:1.5px solid rgba(180,220,255,.7);animation:cuBub linear infinite}' +
    '@keyframes cuBub{to{transform:translateY(-22vh)}}' +
    '#tank .weed{bottom:-6px;transform-origin:50% 100%;animation:cuWeed 4s ease-in-out infinite alternate}' +
    '@keyframes cuWeed{from{transform:rotate(-8deg)}to{transform:rotate(8deg)}}' +
    '#tank .sand{position:absolute;left:0;right:0;bottom:0;height:10px;background:#6b5a3a;border-radius:50% 50% 0 0/10px 10px 0 0}';
  var st = el('style'); st.textContent = css; document.head.appendChild(st);
  var layer = el('div'); layer.id = 'cute'; layer.setAttribute('aria-hidden', 'true'); body.appendChild(layer);

  /* ---------- what's going on today ---------- */
  function night() { return body.classList.contains('night'); }
  function awake() { return !document.hidden && !night(); }
  function cur() { return (typeof W !== 'undefined' && W && W.current) || null; }
  function code() { var c = cur(); return c ? c.weather_code : -1; }
  function raining() { var k = code(); return (k >= 51 && k <= 67) || (k >= 80 && k <= 82) || k >= 95; }
  function snowing() { var k = code(); return (k >= 71 && k <= 77) || k === 85 || k === 86; }
  function cold() { var c = cur(); return snowing() || (!!c && c.temperature_2m <= (cfg.cold == null ? 4 : cfg.cold)); }
  function winter() { var m = new Date().getMonth(); return m === 11 || m <= 1 || snowing(); }
  function fest(d) { try { var f = festOn(d || new Date()); return f ? f[0] : ''; } catch (e) { return ''; } }
  function midAutumn() { for (var i = -1; i <= 1; i++) { var d = new Date(); d.setDate(d.getDate() + i); if (fest(d) === 'midautumn') return true; } return false; }
  function fireworksDay() { var f = fest(); return f === 'newyear' || f === 'cny' || f === 'bonfire'; }
  function birthdays() {
    try {
      if (typeof BDAYS === 'undefined' || !BDAYS || !BDAYS.people) return [];
      var t = new Date(); t.setHours(0, 0, 0, 0);
      return BDAYS.people.filter(function (p) { var q = {}; for (var k in p) q[k] = p[k]; return bdayDays(q, t) === 0; });
    } catch (e) { return []; }
  }
  function pageEl() { var t = $('track'); return t && t.children[typeof PAGE === 'number' ? PAGE : 0]; }
  function clockBox() {   // where the clock is on the page showing now
    var pg = pageEl(), c = pg && (pg.querySelector('#clock') || pg.querySelector('#face'));
    if (!c) return null;
    var r = c.getBoundingClientRect(); return r.width > 50 ? r : null;
  }

  /* ---------- one visitor at a time ---------- */
  var busyUntil = 0, timers = [];
  function clear() { timers.forEach(clearTimeout); timers = []; layer.innerHTML = ''; busyUntil = 0; }
  function at(ms, fn) { timers.push(later(fn, ms)); }
  function play(name, force) {
    if (!SHOW[name]) return false;
    if (!force && (Date.now() < busyUntil || !awake())) return false;
    clear();
    var ms = SHOW[name]();
    busyUntil = Date.now() + ms;
    at(ms, clear);
    return true;
  }

  var SHOW = {};

  /* sleepy cat curled up on the clock: Zzz, wakes, stretches, trots off */
  var CAT = '<svg viewBox="0 0 130 86"><g class="bd">' +
    '<path d="M104 72c18 2 22-16 10-20" fill="none" stroke="#e8964a" stroke-width="9" stroke-linecap="round"/>' +
    '<ellipse class="bth" cx="74" cy="60" rx="40" ry="22" fill="#f2a65a"/>' +
    '<path d="M62 42q4 12 0 24M76 40q4 13 0 26M90 43q3 11 0 22" stroke="#d9823a" stroke-width="4" fill="none" stroke-linecap="round"/>' +
    '<path d="M18 40l4-20 14 12zM46 34l2-20-15 9z" fill="#f2a65a"/><path d="M22 35l2-9 7 6zM43 30l1-10-7 5z" fill="#ffc9b5"/>' +
    '<circle cx="34" cy="50" r="22" fill="#f6b46c"/>' +
    '<g class="shut" stroke="#5a3a26" stroke-width="2.5" fill="none" stroke-linecap="round"><path d="M22 50q4 4 8 0M38 50q4 4 8 0"/></g>' +
    '<g class="open"><circle cx="26" cy="49" r="4.2" fill="#3a2a20"/><circle cx="42" cy="49" r="4.2" fill="#3a2a20"/><circle cx="27.4" cy="47.6" r="1.4" fill="#fff"/><circle cx="43.4" cy="47.6" r="1.4" fill="#fff"/></g>' +
    '<path d="M32 57l2 2 2-2" fill="#e57373"/><path d="M34 59q-3 4-6 1M34 59q3 4 6 1" stroke="#5a3a26" stroke-width="1.6" fill="none"/>' +
    '<circle cx="20" cy="58" r="4" fill="#ffb3b3" opacity=".6"/><circle cx="48" cy="58" r="4" fill="#ffb3b3" opacity=".6"/>' +
    '<ellipse cx="42" cy="76" rx="10" ry="6" fill="#f6b46c"/><ellipse cx="60" cy="79" rx="10" ry="6" fill="#f6b46c"/>' +
    '</g></svg>';
  SHOW.cat = function () {
    var r = clockBox(), w = 130, h = 86, x, y;
    if (r) { x = r.left + r.width * 0.32; y = r.bottom - h - Math.min(10, r.height * 0.03); } else { x = innerWidth - w - 30; y = innerHeight - h - 20; }
    var cat = el('div', 'cat', CAT); cat.style.left = x + 'px'; cat.style.top = y + 'px'; layer.appendChild(cat);
    for (var i = 0; i < 3; i++) { var z = el('div', 'zz', 'z'); z.style.left = (x + 30 + i * 6) + 'px'; z.style.top = (y + 4) + 'px'; z.style.animationDelay = (i * 1) + 's'; z.style.fontSize = (14 + i * 4) + 'px'; layer.appendChild(z); }
    at(5000, function () { [].forEach.call(layer.querySelectorAll('.zz'), function (z) { z.remove(); }); cat.classList.add('wake'); sfx('meow'); });
    at(5600, function () { var b = el('div', 'bub', '喵～ 夠鐘喇!'); b.style.left = (x - 20) + 'px'; b.style.top = (y - 34) + 'px'; layer.appendChild(b); });
    at(6400, function () { cat.classList.add('stretch'); });
    at(8600, function () { var b = layer.querySelector('.bub'); if (b) b.remove(); cat.classList.add('walk'); cat.style.transform = 'translateX(' + (innerWidth - x + 40) + 'px)'; });
    return 13800;
  };

  /* cuckoo: a little wooden house drops down, door opens, bird calls */
  var CUK = '<svg viewBox="0 0 96 120" width="96" height="120"><path d="M48 0v14" stroke="#7a5230" stroke-width="2"/>' +
    '<path d="M4 44L48 12l44 32z" fill="#8d5a33"/><path d="M0 46L48 10l48 36" fill="none" stroke="#5e3a1f" stroke-width="6" stroke-linecap="round"/>' +
    '<rect x="12" y="44" width="72" height="62" rx="4" fill="#c58a52"/>' +
    '<g class="bird"><ellipse cx="48" cy="58" rx="13" ry="11" fill="#7ec8e3"/><circle cx="52" cy="54" r="2.4" fill="#2b2b2b"/><path d="M60 56l9 3-9 3z" fill="#f4a020"/><path d="M38 58q-8-4-6 6" fill="#5fb2d1"/></g>' +
    '<rect x="34" y="44" width="28" height="30" rx="14" ry="14" fill="#3b2412" opacity=".0"/>' +
    '<path class="door" d="M34 74V58a14 14 0 0 1 28 0v16z" fill="#6b3f1f"/>' +
    '<circle cx="48" cy="92" r="9" fill="#fff6e8"/><path d="M48 92V86M48 92l4 2" stroke="#3a2a20" stroke-width="1.8" stroke-linecap="round"/>' +
    '<path d="M38 106v10M58 106v8" stroke="#7a5230" stroke-width="2"/><path d="M33 118l5-4 5 4zM53 116l5-4 5 4z" fill="#d4a24a"/></svg>';
  SHOW.cuckoo = function () {
    var r = clockBox(), x, y;
    if (r) { x = r.left + r.width * 0.5 - 48; y = r.top; } else { x = innerWidth / 2 - 48; y = 0; }
    var box = el('div', 'cuk', CUK); box.style.left = x + 'px'; box.style.top = y + 'px'; layer.appendChild(box);
    var bird = box.querySelector('.bird'); bird.parentNode.appendChild(bird);   // bird in front of the door once it's out
    var calls = Math.max(1, Math.min(3, (new Date().getHours() % 12) % 3 + 1)), t = 900;
    at(t, function () { box.classList.add('open'); });
    for (var i = 0; i < calls; i++) (function (i) {
      at(t + 400 + i * 1300, function () { box.classList.add('out'); sfx('cuckoo'); if (!i) { var b = el('div', 'bub', '咕咕!'); b.style.left = (x + 86) + 'px'; b.style.top = (y + 40) + 'px'; layer.appendChild(b); } });
      at(t + 1100 + i * 1300, function () { box.classList.remove('out'); });
    })(i);
    var end = t + 1300 + calls * 1300;
    at(end, function () { box.classList.remove('open'); var b = layer.querySelector('.bub'); if (b) b.remove(); });
    at(end + 600, function () { box.classList.add('go'); });
    return end + 1300;
  };

  /* winter: snow falls and piles up on the tiles, then melts */
  SHOW.snow = function () {
    for (var i = 0; i < 34; i++) {
      var f = el('div', 'flake', pick(['❄', '❅', '•', '•'])); f.style.left = rand(0, 100) + 'vw'; f.style.fontSize = rand(10, 24) + 'px';
      f.style.setProperty('--dx', rand(-60, 60) + 'px'); f.style.animationDuration = rand(7, 12) + 's'; f.style.animationDelay = rand(0, 6) + 's'; layer.appendChild(f);
    }
    var pg = pageEl(), tiles = pg ? pg.querySelectorAll('.t') : [];
    [].forEach.call(tiles, function (t) {
      var r = t.getBoundingClientRect(); if (r.width < 60 || r.bottom < 0 || r.top > innerHeight) return;
      var c = el('div', 'cap'); c.style.left = (r.left + 8) + 'px'; c.style.width = (r.width - 16) + 'px'; c.style.top = (r.top - 12) + 'px'; c.style.animationDelay = rand(0, 1.5) + 's'; layer.appendChild(c);
    });
    return 18500;
  };

  /* 中秋: lanterns float up */
  SHOW.lanterns = function () {
    for (var i = 0; i < 7; i++) {
      var w = el('div', 'rise'), s = el('span', 'em sway glow', '🏮');
      s.style.fontSize = rand(40, 70) + 'px'; s.style.animationDelay = rand(0, 2) + 's';
      w.style.left = (6 + i * 13 + rand(-3, 3)) + 'vw'; w.style.animationDuration = rand(10, 15) + 's'; w.style.animationDelay = rand(0, 3) + 's';
      w.appendChild(s); layer.appendChild(w);
    }
    var b = el('div', 'banner', '🥮 中秋節快樂 🐇<small>Happy Mid-Autumn Festival</small>'); b.style.color = '#c2571b'; layer.appendChild(b);
    at(9000, function () { b.style.animation = 'cuFade 1s both'; });
    return 18500;
  };

  /* New Year, CNY, Bonfire Night: fireworks on a canvas, only while showing */
  SHOW.fireworks = function () {
    var cv = el('canvas'); cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%'; layer.appendChild(cv);
    var dpr = Math.min(2, window.devicePixelRatio || 1), W2 = cv.width = innerWidth * dpr, H2 = cv.height = innerHeight * dpr, g = cv.getContext('2d');
    var parts = [], start = Date.now(), DUR = 11000, nextBurst = 0, raf = 0;
    var COLS = ['#ff5252', '#ffd740', '#69f0ae', '#40c4ff', '#e040fb', '#ffab40', '#fff'];
    function burst() {
      var x = rand(0.15, 0.85) * W2, y = rand(0.12, 0.45) * H2, col = pick(COLS), n = 46;
      for (var i = 0; i < n; i++) { var a = i / n * Math.PI * 2, v = rand(2, 5.5) * dpr; parts.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 1, col: col }); }
      sfx('pop');
    }
    function frame() {
      var t = Date.now() - start;
      if (t > DUR || !layer.contains(cv)) { cancelAnimationFrame(raf); return; }
      if (t > nextBurst && t < DUR - 2500) { burst(); nextBurst = t + rand(500, 1300); }
      g.clearRect(0, 0, W2, H2);
      for (var i = parts.length - 1; i >= 0; i--) {
        var p = parts[i]; p.x += p.vx; p.y += p.vy; p.vy += 0.06 * dpr; p.vx *= 0.985; p.vy *= 0.985; p.life -= 0.012;
        if (p.life <= 0) { parts.splice(i, 1); continue; }
        g.globalAlpha = p.life; g.fillStyle = p.col; g.beginPath(); g.arc(p.x, p.y, 2.6 * dpr, 0, 6.3); g.fill();
      }
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
    var f = fest(), txt = f === 'cny' ? '🧧 新年快樂 恭喜發財<small>Happy Chinese New Year</small>' : f === 'bonfire' ? '🎆 煙花之夜<small>Bonfire Night</small>' : '🎆 新年快樂<small>Happy New Year</small>';
    var b = el('div', 'banner', txt); b.style.color = '#c62828'; layer.appendChild(b);
    at(7000, function () { b.style.animation = 'cuFade 1s both'; });
    return DUR + 300;
  };

  /* rain: a duck with an umbrella waddles across */
  SHOW.duck = function () {
    var w = el('div', 'walk'); w.style.animationDuration = '14s';
    w.innerHTML = '<span class="waddle"><span class="em" style="position:relative;display:block;font-size:52px;left:14px;top:6px">☂️</span><span class="em" style="position:relative;display:block;font-size:56px">🦆</span></span>';
    layer.appendChild(w);
    at(2500, function () { sfx('quack'); });
    at(4000, function () { var b = el('div', 'bub', '落雨喇，記得帶遮! ☔'); b.style.left = '30vw'; b.style.bottom = 'calc(2.5vh + 130px)'; layer.appendChild(b); });
    at(7500, function () { var b = layer.querySelector('.bub'); if (b) b.style.animation = 'cuFade .6s both'; });
    return 14500;
  };

  /* cold: a snowman pops up in the corner and waves */
  SHOW.snowman = function () {
    var c = cur(), t = c ? Math.round(c.temperature_2m) + '°' : '';
    var s = el('div', 'snowman', '<span class="em" style="font-size:110px;display:block">⛄</span>'); layer.appendChild(s);
    at(100, function () { s.classList.add('up'); });
    at(1300, function () { var b = el('div', 'bub', '好凍呀! Brrr ' + t + ' 🧣'); b.style.left = 'calc(3vw + 100px)'; b.style.bottom = '150px'; layer.appendChild(b); });
    at(8500, function () { s.classList.remove('up'); var b = layer.querySelector('.bub'); if (b) b.remove(); });
    return 10000;
  };

  /* birthdays: balloons float up with a banner */
  SHOW.balloons = function () {
    var who = birthdays().map(function (p) { return p.name; }).filter(Boolean).join('、');
    for (var i = 0; i < 10; i++) {
      var w = el('div', 'rise'), s = el('span', 'em sway', '🎈');
      s.style.fontSize = rand(48, 80) + 'px'; s.style.filter = 'hue-rotate(' + Math.round(rand(0, 360)) + 'deg)'; s.style.animationDelay = rand(0, 2) + 's';
      w.style.left = rand(2, 92) + 'vw'; w.style.animationDuration = rand(8, 12) + 's'; w.style.animationDelay = rand(0, 3) + 's';
      w.appendChild(s); layer.appendChild(w);
    }
    var b = el('div', 'banner', '🎂 生日快樂' + (who ? ' ' + who : '') + '!<small>Happy Birthday!</small>'); layer.appendChild(b);
    at(1000, function () { sfx('pop'); });
    at(9000, function () { b.style.animation = 'cuFade 1s both'; });
    return 15500;
  };

  /* Man United goal: confetti and a cheering little red devil */
  var DEV = '<svg viewBox="0 0 220 240"><path d="M62 70L50 22l34 30zM158 70l12-48-34 30z" fill="#b71c1c"/>' +
    '<path d="M40 140L8 92M180 140l32-48" stroke="#e53935" stroke-width="16" stroke-linecap="round"/><circle cx="8" cy="88" r="11" fill="#e53935"/><circle cx="212" cy="88" r="11" fill="#e53935"/>' +
    '<path d="M70 150h80l10 70H60z" fill="#da291c"/><path d="M70 150h80l3 22H67z" fill="#fff"/><text x="110" y="208" text-anchor="middle" font-family="sans-serif" font-weight="900" font-size="30" fill="#fbe122">7</text>' +
    '<path d="M64 220h40v14H58zM116 220h40l6 14h-46z" fill="#111"/>' +
    '<circle cx="110" cy="96" r="58" fill="#e53935"/>' +
    '<ellipse cx="90" cy="92" rx="10" ry="12" fill="#fff"/><ellipse cx="130" cy="92" rx="10" ry="12" fill="#fff"/><circle cx="92" cy="94" r="6" fill="#222"/><circle cx="128" cy="94" r="6" fill="#222"/>' +
    '<path d="M84 116q26 26 52 0z" fill="#7f0000"/><path d="M96 124q14 8 28 0" fill="#ff8a80"/>' +
    '<circle cx="74" cy="112" r="7" fill="#ff8a80" opacity=".7"/><circle cx="146" cy="112" r="7" fill="#ff8a80" opacity=".7"/></svg>';
  SHOW.goal = function () {
    var COLS = ['#da291c', '#fbe122', '#fff', '#111', '#da291c'];
    for (var i = 0; i < 70; i++) {
      var c = el('div', 'conf'); c.style.left = rand(0, 100) + 'vw'; c.style.background = pick(COLS);
      c.style.setProperty('--dx', rand(-80, 80) + 'px'); c.style.animationDuration = rand(3, 6) + 's'; c.style.animationDelay = rand(0, 3) + 's'; layer.appendChild(c);
    }
    var d = el('div', 'dev', DEV); layer.appendChild(d);
    var g = el('div', 'gl', 'GOAL! ⚽<small>入波喇! Man United</small>'); layer.appendChild(g);
    at(100, function () { d.classList.add('up'); sfx('cheer'); });
    at(2200, function () { sfx('cheer'); });
    at(8000, function () { d.classList.remove('up'); g.style.animation = 'cuFade .8s both'; });
    return 9500;
  };
  C.goal = function () { if (awake()) play('goal', true); };

  /* ---------- night: little fish tank along the bottom of the night clock ---------- */
  function tank() {
    var n = $('night'); if (!n || cfg.fish === false || $('tank')) return;
    var t = el('div'); t.id = 'tank';
    var h = '<div class="sand"></div>';
    ['🌿', '🌱', '🌿', '🪸', '🌿'].forEach(function (e, i) { h += '<span class="em weed" style="left:' + (5 + i * 21) + '%;font-size:' + (34 + (i % 2) * 14) + 'px;animation-delay:-' + i + 's">' + e + '</span>'; });
    [['🐠', 50, 70, 24], ['🐟', 40, 95, 50], ['🐡', 44, 120, 36], ['🐠', 34, 80, 62], ['🐟', 38, 140, 12]].forEach(function (f, i) {
      h += '<span class="em fish" style="top:' + f[3] + '%;font-size:' + f[1] + 'px;animation-duration:' + f[2] + 's;animation-delay:-' + Math.round(f[2] * i / 5) + 's"><i style="animation-delay:-' + i + 's">' + f[0] + '</i></span>';
    });
    for (var i = 0; i < 6; i++) h += '<span class="em bubble" style="left:' + (8 + i * 16) + '%;animation-duration:' + (7 + i % 3 * 3) + 's;animation-delay:-' + i * 2 + 's"></span>';
    t.innerHTML = h; n.appendChild(t);
  }
  tank();

  /* ---------- when visitors come ---------- */
  function pool() {
    var p = [['cat', 3], ['cuckoo', 2]];
    if (winter()) p.push(['snow', 3]);
    if (raining()) p.push(['duck', 4]);
    if (cold()) p.push(['snowman', 3]);
    if (midAutumn()) p.push(['lanterns', 8]);
    if (fireworksDay()) p.push(['fireworks', 8]);
    if (birthdays().length) p.push(['balloons', 10]);
    return p;
  }
  function randomOne() {
    var p = pool(), sum = 0; p.forEach(function (x) { sum += x[1]; });
    var r = Math.random() * sum; for (var i = 0; i < p.length; i++) { r -= p[i][1]; if (r < 0) return p[i][0]; }
    return 'cat';
  }
  var nextAt = Date.now() + rand(1, 3) * 60e3, lastHour = new Date().getHours(), wasRain = null, wasCold = null, bdayShown = '';
  function soon() { nextAt = Date.now() + rand(EVERY[0], EVERY[1]) * 60e3; }
  function check() {
    if (!awake()) { if (night()) clear(); return; }
    var d = new Date(), h = d.getHours();
    if (h !== lastHour && d.getMinutes() === 0) { lastHour = h; if (play(Math.random() < 0.5 ? 'cat' : 'cuckoo')) soon(); return; }
    if (h !== lastHour) lastHour = h;
    if (cur()) {   // weather just changed
      var rn = raining(), cd = cold();
      if (wasRain === false && rn && play('duck')) { wasRain = rn; soon(); return; }
      if (wasCold === false && cd && play('snowman')) { wasCold = cd; soon(); return; }
      wasRain = rn; wasCold = cd;
    }
    var bk = d.toDateString();
    if (bdayShown !== bk && birthdays().length && play('balloons')) { bdayShown = bk; soon(); return; }
    if (Date.now() >= nextAt) { if (play(randomOne())) soon(); }
  }
  setInterval(check, 5000);
  document.addEventListener('visibilitychange', function () { if (document.hidden) clear(); });

  /* ?cute=name shows one now (all = each in turn) */
  var test = new URLSearchParams(location.search).get('cute');
  if (test) {
    var list = test === 'all' ? ['cat', 'cuckoo', 'snow', 'lanterns', 'fireworks', 'duck', 'snowman', 'goal', 'balloons'] : [test], k = 0;
    nextAt = 1e15;
    setTimeout(function go() { if (k < list.length) { play(list[k++], true); setTimeout(go, Math.max(busyUntil - Date.now() + 800, 1500)); } }, 1500);
  }
  C.play = function (n) { return play(n, true); };
})();
