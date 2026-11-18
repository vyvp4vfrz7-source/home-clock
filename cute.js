/* Cute visitors: little animations that pop up now and then, never blocking a tap.
   - On the hour: the sleepy cat wakes and stretches, or the cuckoo pops out.
   - Every few minutes (CONFIG.cute.every, minutes): a random visitor that fits today.
   - Triggered: duck with umbrella when rain starts, snowman when it turns cold, a goal party when
     Man United score, birthday balloons, 中秋 lanterns, New Year / CNY / Bonfire Night fireworks, winter snow.
   - At night: a dim little fish tank along the bottom of the night clock.
   - 波波 the Pomeranian drops by in 10 ways: zoomies, ball, nap on the clock, peekaboo, chases the cat, digs up a bone,
     butterfly + sneeze, tail chase, photobomb, begs for a treat. Every CONFIG.cute.dog minutes ([0] = 0 turns it off),
     and 30 s after the page loads or the night clock ends.
   Sounds go through sound.js (silent unless the speaker is turned up, never at night).
   Try one now with ?cute=cat|cuckoo|snow|lanterns|fireworks|duck|snowman|goal|balloons|all, the dog with
   ?cute=pom (random) | pom-zoom|pom-ball|pom-nap|pom-peek|pom-cat|pom-dig|pom-fly|pom-spin|pom-photo|pom-beg | pom-all, fish with ?night=1. */
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

  /* ---------- 波波 the Pomeranian: our own fluffy dog drops by in 10 different ways ---------- */
  var POM_C = { fur: '#f2b47a', dark: '#e39a5c', light: '#f8cf9f', cream: '#fdf1de', ear: '#f6c3b0', eye: '#2a1d19', nose: '#4b2c28', tongue: '#f2828f' };
  function fluff(cx, cy, rx, ry, n, r, col) {   // a ring of little circles = fluffy outline
    var s = ''; for (var i = 0; i < n; i++) { var a = i / n * 6.283; s += '<circle cx="' + (cx + Math.cos(a) * rx).toFixed(1) + '" cy="' + (cy + Math.sin(a) * ry).toFixed(1) + '" r="' + r + '" fill="' + col + '"/>'; }
    return s;
  }
  var EYES = '<g class="op"><circle cx="0" cy="0" r="5.2" fill="' + POM_C.eye + '"/><circle cx="1.6" cy="-1.8" r="1.8" fill="#fff"/><circle cx="-1.6" cy="1.8" r=".8" fill="#fff"/></g>' +
    '<path class="sh" d="M-5 0q5 4 10 0" stroke="' + POM_C.eye + '" stroke-width="2.2" fill="none" stroke-linecap="round"/>';
  /* side view, facing right; legs, tail and eyes move with CSS classes */
  var POM_SIDE = '<svg viewBox="0 0 130 104"><g class="bod">' +
    '<g class="tl">' + fluff(30, 38, 13, 10, 9, 8, POM_C.light) + '<ellipse cx="30" cy="38" rx="14" ry="11" fill="' + POM_C.cream + '"/></g>' +
    '<g class="lg"><rect class="l1" x="30" y="66" width="11" height="26" rx="5.5" fill="' + POM_C.dark + '"/><rect class="l2" x="70" y="66" width="11" height="26" rx="5.5" fill="' + POM_C.dark + '"/></g>' +
    fluff(54, 64, 30, 19, 14, 9, POM_C.fur) + '<ellipse cx="54" cy="64" rx="31" ry="20" fill="' + POM_C.fur + '"/>' +
    '<ellipse cx="78" cy="70" rx="15" ry="15" fill="' + POM_C.cream + '"/>' + fluff(78, 72, 12, 12, 8, 6, POM_C.cream) +
    '<g class="lg"><rect class="l3" x="40" y="68" width="12" height="26" rx="6" fill="' + POM_C.fur + '"/><rect class="l4" x="80" y="68" width="12" height="26" rx="6" fill="' + POM_C.cream + '"/>' +
      '<ellipse class="l3" cx="46" cy="93" rx="7.5" ry="4.5" fill="' + POM_C.cream + '"/><ellipse class="l4" cx="86" cy="93" rx="7.5" ry="4.5" fill="' + POM_C.cream + '"/></g>' +
    '<g class="hd">' +
      '<path d="M76 22L80 2l14 16zM98 18l12-14 2 22z" fill="' + POM_C.dark + '"/><path d="M80 18l2-10 7 8zM102 17l7-8 1 12z" fill="' + POM_C.ear + '"/>' +
      fluff(94, 38, 23, 21, 15, 8, POM_C.fur) + '<circle cx="94" cy="38" r="24" fill="' + POM_C.light + '"/>' +
      '<ellipse cx="108" cy="48" rx="13" ry="10" fill="' + POM_C.cream + '"/>' +
      '<g transform="translate(102 35)">' + EYES + '</g>' +
      '<ellipse cx="119" cy="44" rx="5" ry="4" fill="' + POM_C.nose + '"/><ellipse cx="118" cy="42.6" rx="1.8" ry="1" fill="#fff" opacity=".5"/>' +
      '<g class="mo"><path d="M104 52q6 8 14 0z" fill="#7a3a3a"/><path class="tg" d="M107 54q4 10 9 0z" fill="' + POM_C.tongue + '"/></g>' +
      '<circle cx="96" cy="48" r="4.5" fill="#ff9e9e" opacity=".45"/>' +
    '</g><g class="held"></g></g></svg>';
  /* front view, sitting, like the photo */
  var POM_FRONT = '<svg viewBox="0 0 130 140"><g class="bod">' +
    '<g class="tl">' + fluff(100, 100, 12, 10, 8, 8, POM_C.light) + '</g>' +
    fluff(65, 106, 32, 26, 14, 9, POM_C.fur) + '<ellipse cx="65" cy="106" rx="33" ry="27" fill="' + POM_C.fur + '"/>' +
    '<ellipse cx="65" cy="104" rx="22" ry="24" fill="' + POM_C.cream + '"/>' + fluff(65, 98, 20, 16, 10, 7, POM_C.cream) +
    '<g class="pw"><ellipse cx="52" cy="130" rx="9" ry="6" fill="' + POM_C.cream + '"/><ellipse cx="78" cy="130" rx="9" ry="6" fill="' + POM_C.cream + '"/></g>' +
    '<g class="hd">' +
      '<path d="M32 40L36 6l26 22zM98 40L94 6 68 28z" fill="' + POM_C.dark + '"/><path d="M38 32l2-18 13 12zM92 32l-2-18-13 12z" fill="' + POM_C.ear + '"/>' +
      fluff(65, 52, 32, 28, 18, 9, POM_C.fur) + '<ellipse cx="65" cy="52" rx="33" ry="30" fill="' + POM_C.light + '"/>' +
      '<path d="M40 40q25-14 50 0" stroke="' + POM_C.fur + '" stroke-width="6" fill="none" opacity=".6"/>' +
      '<ellipse cx="65" cy="68" rx="18" ry="13" fill="' + POM_C.cream + '"/>' +
      '<g transform="translate(51 51) scale(1.2)">' + EYES + '</g><g transform="translate(79 51) scale(1.2)">' + EYES + '</g>' +
      '<ellipse cx="65" cy="62" rx="6.5" ry="5" fill="' + POM_C.nose + '"/><ellipse cx="63.5" cy="60.5" rx="2.2" ry="1.2" fill="#fff" opacity=".5"/>' +
      '<g class="mo"><path d="M56 69q9 13 18 0z" fill="#7a3a3a"/><path class="tg" d="M59 72q6 12 12 0z" fill="' + POM_C.tongue + '"/></g>' +
      '<circle cx="44" cy="66" r="5" fill="#ff9e9e" opacity=".45"/><circle cx="86" cy="66" r="5" fill="#ff9e9e" opacity=".45"/>' +
    '</g></g></svg>';
  var POM_CSS =
    '#cute .pom{position:absolute;left:0;top:0;width:130px;height:104px;will-change:transform}' +
    '#cute .pom.fr{height:140px}' +
    '#cute .pom .fl{width:100%;height:100%;transition:transform .25s}#cute .pom.left .fl{transform:scaleX(-1)}' +
    '#cute .pom svg{width:100%;height:100%;overflow:visible}' +
    '#cute .pom .sh,#cute .pom.sleep .op{display:none}#cute .pom.sleep .sh,#cute .pom.blink .sh{display:inline}#cute .pom.blink .op{display:none}' +
    '#cute .pom .lg rect,#cute .pom .lg ellipse{transform-box:fill-box;transform-origin:50% 0}' +
    '#cute .pom.run .l1,#cute .pom.run .l4{animation:pmLeg .22s ease-in-out infinite alternate}' +
    '#cute .pom.run .l2,#cute .pom.run .l3{animation:pmLeg .22s ease-in-out infinite alternate-reverse}' +
    '@keyframes pmLeg{from{transform:rotate(-32deg)}to{transform:rotate(32deg)}}' +
    '#cute .pom.run .bod{animation:pmBob .22s ease-in-out infinite alternate}' +
    '@keyframes pmBob{to{transform:translateY(-6px)}}' +
    '#cute .pom .tl{transform-box:fill-box;transform-origin:80% 80%;animation:pmWag .3s ease-in-out infinite alternate}' +
    '@keyframes pmWag{from{transform:rotate(-12deg)}to{transform:rotate(14deg)}}' +
    '#cute .pom .tg{transform-box:fill-box;transform-origin:50% 0;animation:pmPant .3s ease-in-out infinite alternate}' +
    '@keyframes pmPant{to{transform:scaleY(1.25)}}' +
    '#cute .pom.sleep .mo,#cute .pom.sleep .lg{display:none}#cute .pom.sleep .bod{transform:translateY(10px)}#cute .pom.sleep .tl{animation:none}' +
    '#cute .pom.sleep .bod>*{animation:none}' +
    '#cute .pom.stretch .bod{transform-box:view-box;transform-origin:65px 95px;animation:pmStretch 1.6s ease-in-out}' +
    '@keyframes pmStretch{40%,60%{transform:scaleX(1.18) scaleY(.88)}}' +
    '#cute .pom.dig .l2,#cute .pom.dig .l4{animation:pmLeg .12s linear infinite alternate}#cute .pom.dig .hd{transform-box:view-box;transform-origin:90px 60px;transform:rotate(18deg)}' +
    '#cute .pom.hop .bod{animation:pmHop .5s ease-out infinite}' +
    '@keyframes pmHop{0%,100%{transform:none}40%{transform:translateY(-34px) rotate(-8deg)}}' +
    '#cute .pom.jump .bod{animation:pmHop .6s ease-out 2}' +
    '#cute .pom.beg .pw{animation:pmBeg .35s ease-in-out infinite alternate}' +
    '@keyframes pmBeg{to{transform:translateY(-26px)}}' +
    '#cute .pom.beg .bod{transform-box:view-box;transform-origin:65px 140px;animation:pmTilt 1.2s ease-in-out infinite alternate}' +
    '@keyframes pmTilt{from{transform:rotate(-5deg)}to{transform:rotate(5deg)}}' +
    '#cute .pom.ears .hd{transform-box:view-box;transform-origin:65px 60px;animation:pmTilt .5s ease-in-out 4 alternate}' +
    '#cute .pom.spin .fl{animation:pmSpin 1s linear infinite}' +
    '@keyframes pmSpin{0%{transform:translate(0,0) scaleX(1)}25%{transform:translate(50px,-16px) scaleX(1)}26%{transform:translate(50px,-16px) scaleX(-1)}50%{transform:translate(0,-28px) scaleX(-1)}75%{transform:translate(-50px,-16px) scaleX(-1)}76%{transform:translate(-50px,-16px) scaleX(1)}100%{transform:translate(0,0) scaleX(1)}}' +
    '#cute .pom.dizzy .bod{transform-box:view-box;transform-origin:65px 100px;animation:pmTilt .45s ease-in-out infinite alternate}' +
    '#cute .pmball{position:absolute;left:0;top:0;width:34px;height:34px;font-size:32px;line-height:1}' +
    '#cute .pmball i{display:block;font-style:normal;animation:pmBounce .45s cubic-bezier(.3,0,.7,1) infinite alternate}' +
    '@keyframes pmBounce{from{transform:translateY(-70px) rotate(0)}to{transform:translateY(0) rotate(200deg)}}' +
    '#cute .dirt{position:absolute;width:9px;height:9px;border-radius:50%;background:#8a5a32;animation:pmDirt .7s ease-out both}' +
    '@keyframes pmDirt{0%{transform:none;opacity:1}100%{transform:translate(var(--dx),var(--dy));opacity:0}}' +
    '#cute .mound{position:absolute;width:70px;height:26px;border-radius:50% 50% 0 0;background:#9a6a3c;transform-origin:50% 100%;transform:scaleY(0);transition:transform 3s}' +
    '#cute .heart{position:absolute;font-size:26px;animation:pmHeart 2.2s ease-out both;color:#ff6f91}' +
    '@keyframes pmHeart{0%{transform:scale(.3);opacity:0}20%{opacity:1}100%{transform:translate(var(--dx),-120px) scale(1.2);opacity:0}}' +
    '#cute .puff{position:absolute;font-size:24px;animation:pmPuff .8s ease-out both}' +
    '@keyframes pmPuff{to{transform:translate(var(--dx),-14px) scale(1.6);opacity:0}}' +
    '#cute .peek{position:absolute;overflow:hidden;width:150px;height:110px}' +
    '#cute .peek .pom{transition:transform .7s cubic-bezier(.3,1.4,.6,1)}' +
    '#cute .fly{position:absolute;left:0;top:0;font-size:34px;transition:transform 1.4s ease-in-out}' +
    '#cute .fly i{display:block;font-style:normal;animation:pmFlap .18s ease-in-out infinite alternate}@keyframes pmFlap{to{transform:scaleX(.5)}}';
  var pst = el('style'); pst.textContent = POM_CSS; document.head.appendChild(pst);

  function ground() { return innerHeight - 104 - Math.max(16, innerHeight * 0.025); }
  function dog(front) {   // a new dog, parked off screen
    var d = el('div', 'pom' + (front ? ' fr' : ''), '<div class="fl">' + (front ? POM_FRONT : POM_SIDE) + '</div>');
    d.x = -200; d.y = ground(); d.style.transform = 'translate3d(-200px,' + d.y + 'px,0)';
    layer.appendChild(d); return d;
  }
  function go(d, x, y, ms, ease) {   // move the dog; faces where it is going
    if (x < d.x - 2) d.classList.add('left'); else if (x > d.x + 2) d.classList.remove('left');
    d.style.transition = 'transform ' + ms + 'ms ' + (ease || 'linear');
    d.x = x; d.y = y == null ? d.y : y;
    d.style.transform = 'translate3d(' + x + 'px,' + d.y + 'px,0)';
  }
  function place(d, x, y) { d.style.transition = 'none'; d.x = x; d.y = y; d.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0)'; }
  function say(txt, x, y, ms) { var b = el('div', 'bub', txt); b.style.left = x + 'px'; b.style.top = y + 'px'; layer.appendChild(b); at(ms || 1800, function () { b.style.animation = 'cuFade .4s both'; }); return b; }
  function hearts(x, y, n) { for (var i = 0; i < (n || 5); i++) { var h = el('div', 'heart', pick(['❤', '💕', '💛'])); h.style.left = (x + rand(-30, 30)) + 'px'; h.style.top = y + 'px'; h.style.setProperty('--dx', rand(-40, 40) + 'px'); h.style.animationDelay = (i * 0.25) + 's'; layer.appendChild(h); } }
  function puffs(d, n) { for (var i = 0; i < n; i++) at(i * 220, function () { var p = el('div', 'puff em', '💨'); var back = d.classList.contains('left'); p.style.left = (d.x + (back ? 110 : -10)) + 'px'; p.style.top = (d.y + 70) + 'px'; p.style.setProperty('--dx', (back ? 30 : -30) + 'px'); if (!back) p.style.transform = 'scaleX(-1)'; layer.appendChild(p); }); }
  function woof() { sfx('woof'); }
  var Wd = function () { return innerWidth; };

  var POM = {};
  /* 1. zoomies: tears across the bottom, back again, and off */
  POM.zoom = function () {
    var d = dog(), g = ground(); d.classList.add('run');
    at(50, function () { go(d, Wd() - 180, g, 2000); puffs(d, 8); });
    at(2100, function () { woof(); say('汪汪! 💨', Wd() - 220, g - 40, 1200); go(d, 120, g, 1900); puffs(d, 8); });
    at(4100, function () { go(d, Wd() * 0.55, g, 1100); });
    at(5300, function () { go(d, Wd() + 200, g, 1500); });
    return 7200;
  };
  /* 2. ball: a tennis ball bounces past, the dog chases it and brings it back */
  POM.ball = function () {
    var g = ground(), b = el('div', 'pmball em', '<i>🎾</i>'); layer.appendChild(b);
    b.style.transform = 'translate3d(' + (Wd() + 60) + 'px,' + (g + 66) + 'px,0)';
    at(50, function () { b.style.transition = 'transform 3.2s linear'; b.style.transform = 'translate3d(-80px,' + (g + 66) + 'px,0)'; });
    var d = dog(); place(d, Wd() + 60, g); d.classList.add('run', 'left');
    at(900, function () { woof(); go(d, -220, g, 3400); });
    at(4600, function () {   // back with the ball in its mouth
      b.remove(); d.querySelector('.held').innerHTML = '<text x="106" y="64" font-size="26">🎾</text>'; d.querySelector('.mo').style.display = 'none';
      go(d, Wd() * 0.45, g, 2000);
    });
    at(6700, function () { d.classList.remove('run'); d.classList.add('jump'); say('再掟多次! 🎾', d.x + 30, g - 46, 2000); hearts(d.x + 80, g, 4); });
    at(8800, function () { d.classList.remove('jump'); d.classList.add('run'); go(d, Wd() + 200, g, 2000); });
    return 11000;
  };
  /* 3. nap: trots onto the clock tile, curls up for a snooze, wakes and stretches */
  POM.nap = function () {
    var r = clockBox(), d = dog(), x, y;
    if (r) { x = r.left + r.width * 0.6; y = r.bottom - 104 - Math.min(10, r.height * 0.03); } else { x = Wd() * 0.6; y = ground(); }
    place(d, -160, y); d.classList.add('run');
    at(50, function () { go(d, x, y, 2400); });
    at(2500, function () { d.classList.remove('run'); d.classList.add('sleep'); });
    for (var i = 0; i < 3; i++) (function (i) { at(2700, function () { var z = el('div', 'zz', 'z'); z.style.left = (x + 100 + i * 6) + 'px'; z.style.top = (y + 6) + 'px'; z.style.animationDelay = i + 's'; z.style.fontSize = (14 + i * 4) + 'px'; layer.appendChild(z); }); })(i);
    at(8500, function () { [].forEach.call(layer.querySelectorAll('.zz'), function (z) { z.remove(); }); d.classList.remove('sleep'); d.classList.add('stretch'); });
    at(9000, function () { woof(); say('瞓醒喇~ 🐾', x - 10, y - 38, 1800); });
    at(10300, function () { d.classList.remove('stretch'); d.classList.add('run'); go(d, Wd() + 200, y, 2200); });
    return 12800;
  };
  /* 4. peekaboo: pops up from the bottom edge, ducks, then peeks somewhere else */
  POM.peek = function () {
    var spots = [rand(0.1, 0.35), rand(0.6, 0.85)], t = 100;
    spots.forEach(function (s, i) {
      var box = el('div', 'peek'); box.style.left = (Wd() * s) + 'px'; box.style.top = (innerHeight - 110) + 'px';
      var d = el('div', 'pom fr', '<div class="fl">' + POM_FRONT + '</div>'); d.style.left = '10px'; d.style.transform = 'translateY(150px)';
      box.appendChild(d); layer.appendChild(box);
      at(t, function () { d.style.transform = 'translateY(20px)'; });
      at(t + 900, function () { d.classList.add('ears'); if (!i) say('👀 邊個喺度?', Wd() * s + 120, innerHeight - 140, 1600); else woof(); });
      at(t + 1600, function () { d.classList.add('blink'); });
      at(t + 1800, function () { d.classList.remove('blink'); });
      at(t + 3000, function () { d.style.transform = 'translateY(150px)'; });
      t += 3700;
    });
    return t + 600;
  };
  /* 5. chases the cat across the screen, then the cat turns round and chases the dog back */
  POM.cat = function () {
    var g = ground(), c = el('div', 'cat wake', CAT); c.querySelector('svg').style.animation = 'cuBob .3s ease-in-out infinite alternate'; c.style.left = '0'; c.style.top = (g + 18) + 'px'; layer.appendChild(c);
    c.style.transition = 'none'; c.style.transform = 'translateX(' + (Wd() + 40) + 'px)';
    var d = dog(); place(d, Wd() + 60, g); d.classList.add('run', 'left');
    at(60, function () { c.style.transition = 'transform 3s linear'; c.style.transform = 'translateX(' + (Wd() * 0.15) + 'px)'; sfx('meow'); });
    at(500, function () { woof(); go(d, Wd() * 0.15 + 170, g, 2600); });
    at(3150, function () { say('喵!!! 😾', Wd() * 0.15, g - 30, 1400); c.querySelector('svg').style.transform = 'scaleX(-1)'; d.classList.remove('run'); });
    at(4000, function () { say('😳', d.x + 60, g - 30, 900); });
    at(4600, function () { d.classList.add('run'); go(d, Wd() + 220, g, 2200); c.style.transition = 'transform 2.8s linear'; c.style.transform = 'translateX(' + (Wd() + 80) + 'px)'; puffs(d, 6); });
    return 7800;
  };
  /* 6. digs a hole and finds a bone */
  POM.dig = function () {
    var g = ground(), x = Wd() * rand(0.3, 0.6), d = dog(), m = el('div', 'mound');
    m.style.left = (x + 110) + 'px'; m.style.top = (g + 78) + 'px'; layer.appendChild(m);
    place(d, -160, g); d.classList.add('run');
    at(50, function () { go(d, x, g, 2000); });
    at(2100, function () { d.classList.remove('run'); d.classList.add('dig'); m.style.transform = 'scaleY(1)'; });
    for (var i = 0; i < 26; i++) at(2200 + i * 130, function () {
      var p = el('div', 'dirt'); p.style.left = (x + 128) + 'px'; p.style.top = (g + 84) + 'px';
      p.style.setProperty('--dx', rand(20, 90) + 'px'); p.style.setProperty('--dy', rand(-70, -20) + 'px'); layer.appendChild(p);
      at(800, function () { p.remove(); });
    });
    var bone;
    at(5800, function () { d.classList.remove('dig'); bone = el('div', 'em', '🦴'); bone.style.cssText = 'position:absolute;font-size:38px;left:' + (x + 125) + 'px;top:' + (g + 60) + 'px;animation:cuPop .4s ease-out both'; layer.appendChild(bone); });
    at(6400, function () { woof(); d.classList.add('jump'); say('搵到喇! 🦴✨', x + 20, g - 44, 1800); hearts(x + 80, g, 4); });
    at(8400, function () { bone.remove(); d.classList.remove('jump'); d.querySelector('.held').innerHTML = '<text x="100" y="62" font-size="26">🦴</text>'; d.classList.add('run'); go(d, -220, g, 2200); m.style.transition = 'transform 1.5s'; m.style.transform = 'scaleY(0)'; });
    return 10800;
  };
  /* 7. hops after a butterfly; it lands on the dog's nose, achoo! */
  POM.fly = function () {
    var g = ground(), f = el('div', 'fly em', '<i>🦋</i>'); layer.appendChild(f);
    var path = [[0.1, 0.55], [0.3, 0.7], [0.5, 0.58], [0.7, 0.72]], d = dog();
    f.style.transform = 'translate3d(-40px,' + (innerHeight * 0.6) + 'px,0)';
    place(d, -200, g); d.classList.add('hop');
    path.forEach(function (p, i) { at(100 + i * 1400, function () { f.style.transform = 'translate3d(' + (Wd() * p[0]) + 'px,' + (innerHeight * p[1]) + 'px,0)'; go(d, Wd() * p[0] - 140, g, 1400); }); });
    at(5800, function () { d.classList.remove('hop'); f.style.transform = 'translate3d(' + (d.x + 104) + 'px,' + (g + 14) + 'px,0)'; });
    at(6300, function () { say('?', d.x + 80, g - 30, 1200); });
    at(7600, function () { sfx('pop'); say('哈啾! 🤧', d.x + 40, g - 40, 1400); d.classList.add('jump'); f.style.transform = 'translate3d(' + (d.x + 260) + 'px,-80px,0)'; });
    at(9000, function () { d.classList.remove('jump'); d.classList.add('run'); go(d, Wd() + 200, g, 2400); });
    return 11600;
  };
  /* 8. chases its own tail round and round, then goes dizzy */
  POM.spin = function () {
    var g = ground(), x = Wd() * 0.45, d = dog(); place(d, -160, g); d.classList.add('run');
    at(50, function () { go(d, x, g, 2000); });
    at(2100, function () { d.classList.add('spin'); say('條尾呢? 🌀', x + 30, g - 70, 1600); });
    at(6200, function () { d.classList.remove('spin', 'run'); d.classList.add('dizzy', 'blink'); say('💫 暈暈地…', x + 20, g - 40, 2000); });
    at(8600, function () { d.classList.remove('dizzy', 'blink'); d.classList.add('run'); go(d, Wd() + 200, g, 2000); });
    return 10800;
  };
  /* 9. photobomb: pops up in front of the family photo and says hi */
  POM.photo = function () {
    var pg = pageEl(), t = pg && pg.querySelector('#photo'), r = t && t.getBoundingClientRect();
    if (!r || r.width < 100) r = { left: Wd() * 0.4, width: 300, bottom: innerHeight - 10, top: innerHeight - 300 };
    var box = el('div', 'peek'); box.style.width = '170px'; box.style.height = '150px';
    box.style.left = (r.left + r.width * 0.62) + 'px'; box.style.top = (r.bottom - 150) + 'px';
    var d = el('div', 'pom fr', '<div class="fl">' + POM_FRONT + '</div>'); d.style.left = '20px'; d.style.transform = 'translateY(170px)';
    box.appendChild(d); layer.appendChild(box);
    var bx = r.left + r.width * 0.62;
    at(100, function () { d.style.transform = 'translateY(8px)'; });
    at(900, function () { woof(); say('Hi! 我都要影埋 📸', bx - 120, r.bottom - 200, 2600); hearts(bx + 85, r.bottom - 140, 6); });
    at(2200, function () { d.classList.add('ears'); });
    at(3600, function () { d.classList.add('blink'); });
    at(3900, function () { d.classList.remove('blink'); });
    at(5600, function () { d.style.transform = 'translateY(170px)'; });
    return 6600;
  };
  /* 10. sits up and begs; a treat drops from the sky */
  POM.beg = function () {
    var g = ground(), x = Wd() * 0.5 - 65, d = dog(); place(d, -160, g); d.classList.add('run');
    at(50, function () { go(d, x, g, 2200); });
    var f;
    at(2300, function () {
      d.remove(); f = el('div', 'pom fr beg', '<div class="fl">' + POM_FRONT + '</div>'); f.style.transform = 'translate3d(' + x + 'px,' + (g - 36) + 'px,0)'; layer.appendChild(f);
      say('俾啲嘢我食吖~ 🥺', x + 70, g - 80, 2200);
    });
    var tr;
    at(4400, function () { tr = el('div', 'em', '🍖'); tr.style.cssText = 'position:absolute;font-size:34px;left:' + (x + 48) + 'px;top:-50px;transition:transform 1.1s cubic-bezier(.5,0,1,1)'; layer.appendChild(tr); });
    at(4500, function () { tr.style.transform = 'translateY(' + (g + 10) + 'px)'; });
    at(5600, function () { tr.remove(); f.classList.remove('beg'); f.classList.add('jump'); woof(); hearts(x + 65, g - 20, 6); say('多謝晒! ❤', x + 70, g - 80, 1800); });
    at(7800, function () { f.remove(); d = dog(); place(d, x, g); d.classList.add('run'); at(30, function () { go(d, Wd() + 200, g, 1800); }); });
    return 10000;
  };
  var POMS = ['zoom', 'ball', 'nap', 'peek', 'cat', 'dig', 'fly', 'spin', 'photo', 'beg'], pomLast = '';
  Object.keys(POM).forEach(function (k) { SHOW['pom-' + k] = POM[k]; });
  SHOW.pom = function () {   // a random one, not the same twice in a row
    var k; do { k = pick(POMS); } while (k === pomLast); pomLast = k;
    return POM[k]();
  };

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
    var p = [['cat', 3], ['cuckoo', 2], ['pom', cfg.pom || 0]];
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
  /* 波波 has its own timer so it is seen often: 30 s after the page loads or the night clock ends, then every CONFIG.cute.dog minutes */
  var DOG = cfg.dog || [5, 10], dogAt = Date.now() + 30e3, wasAwake = true;
  function check() {
    if (!awake()) { if (night()) { clear(); wasAwake = false; } return; }
    if (!wasAwake) { wasAwake = true; dogAt = Date.now() + 20e3; }
    if (DOG[0] > 0 && Date.now() >= dogAt) { if (play('pom')) { dogAt = Date.now() + rand(DOG[0], DOG[1]) * 60e3; return; } dogAt = Date.now() + 15e3; }
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
    var list = test === 'all' ? ['cat', 'cuckoo', 'snow', 'lanterns', 'fireworks', 'duck', 'snowman', 'goal', 'balloons'].concat(POMS.map(function (k) { return 'pom-' + k; })) : test === 'pom-all' ? POMS.map(function (k) { return 'pom-' + k; }) : [test], k = 0;
    nextAt = 1e15;
    setTimeout(function go() { if (k < list.length) { play(list[k++], true); setTimeout(go, Math.max(busyUntil - Date.now() + 800, 1500)); } }, 1500);
  }
  C.play = function (n) { return play(n, true); };
})();
