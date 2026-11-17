/* Sound for the photo slideshows (index.html and parents/index.html).
   - Album videos play WITH sound. iPad Safari lets a page make sound only after a tap on it, so after a
     (re)load the videos play silently, and the speaker button glows, until the first tap anywhere.
     Two <video> elements are reused for every video so that one tap's permission keeps working.
   - The speaker button (shown while a video plays) steps the volume 🔇 → 🔈 → 🔉 → 🔊.
     Safari ignores video.volume, so the sound runs through a Web Audio gain.
   - The 🎵 button picks background music: 關 Off (default), 輕音樂 soft music (made in the page, no
     files or account needed), or Spotify (opens the Spotify app; it can't play inside this page).
     Soft music turns down while a video plays with sound, and stops at night.
   Choices are remembered on each iPad (localStorage: vidVol, bgm). */
(function () {
  var HS = window.HomeSound = {};
  var ICON = ['🔇', '🔈', '🔉', '🔊'], GAIN = [0, 0.2, 0.5, 1], MUSIC_LEVEL = 0.13;
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  var vol = Math.min(3, Math.max(0, +(get('vidVol') || 0) || 0));   // 0 = off until someone turns it up
  var music = get('bgm') === 'soft' ? 'soft' : 'off';
  var pool = [], next = 0, seq = 0, now = null, actx = null, vgain = null, mgain = null, ok = false, quiet = false, first = '';
  var ui = [];
  for (var i = 0; i < 2; i++) { var v = document.createElement('video'); v.muted = true; v.setAttribute('playsinline', ''); v.setAttribute('webkit-playsinline', ''); v.preload = 'auto'; pool.push(v); }

  function soundOn() { return vol > 0 && ok; }
  function ctx() {
    if (actx) return actx;
    try {
      var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
      actx = new AC();
      try { var g = actx.createGain(); pool.forEach(function (v) { actx.createMediaElementSource(v).connect(g); }); g.connect(actx.destination); vgain = g; } catch (e) { vgain = null; }
    } catch (e) { actx = null; }
    return actx;
  }
  function refresh() {
    if (vgain) vgain.gain.value = GAIN[vol];
    if (now) now.muted = !soundOn();
    if (mgain && actx) { var t = actx.currentTime, target = (music === 'soft' && ok && !quiet) ? MUSIC_LEVEL * (now && soundOn() ? 0.2 : 1) : 0; mgain.gain.cancelScheduledValues(t); mgain.gain.setValueAtTime(mgain.gain.value, t); mgain.gain.linearRampToValueAtTime(target, t + 1.5); }
    musicLoop();
    ui.forEach(function (u) { u.vol.textContent = ICON[vol]; u.vol.classList.toggle('ask', vol > 0 && !ok); u.box.classList.toggle('vid', !!now); u.mus.classList.toggle('on', music === 'soft'); u.menu.querySelectorAll('[data-m]').forEach(function (b) { b.classList.toggle('sel', b.getAttribute('data-m') === music); }); });
  }

  /* Call inside a tap: lets this page make sound until it reloads. */
  function unlock() {
    if (actx && actx.state !== 'running' && actx.resume) actx.resume();
    if (ok || (!vol && music === 'off')) return;
    var c = ctx(); if (c && c.resume) c.resume();
    pool.forEach(function (v) {
      if (v === now) return;   // playing now: unmuting it is enough
      var had = v.getAttribute('src'); if (!had && !first) return;
      if (!had) v.src = first;
      try { var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); v.pause(); } catch (e) {}
      if (!had) { v.removeAttribute('src'); try { v.load(); } catch (e) {} }
    });
    ok = true; refresh();
  }
  ['touchend', 'click'].forEach(function (t) { document.addEventListener(t, unlock, true); });

  /* ---- soft music: slow warm chords + a few quiet bell notes, made with Web Audio ---- */
  var CHORDS = [[48, 55, 64, 71, 74], [45, 52, 60, 67, 71], [41, 48, 57, 64, 67], [43, 50, 59, 62, 69]], BELL = [72, 74, 76, 79, 81, 84];
  var chord = 0, mTimer = null, out = null;
  function hz(m) { return 440 * Math.pow(2, (m - 69) / 12); }
  function musicGraph() {
    if (mgain || !ctx()) return !!mgain;
    mgain = actx.createGain(); mgain.gain.value = 0;
    var lp = actx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1400;
    var dl = actx.createDelay(1), fb = actx.createGain(); dl.delayTime.value = 0.42; fb.gain.value = 0.32;
    out = actx.createGain(); out.connect(lp); out.connect(dl); dl.connect(fb); fb.connect(dl); dl.connect(lp); lp.connect(mgain); mgain.connect(actx.destination);
    return true;
  }
  function tone(m, at, len, peak, type) {
    var o = actx.createOscillator(), g = actx.createGain(); o.type = type; o.frequency.value = hz(m); o.detune.value = (Math.random() - 0.5) * 8;
    g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(peak, at + Math.min(2.5, len / 3)); g.gain.linearRampToValueAtTime(0, at + len);
    o.connect(g); g.connect(out); o.start(at); o.stop(at + len + 0.1);
  }
  function bar() {
    var t = actx.currentTime + 0.05, c = CHORDS[chord++ % CHORDS.length];
    c.forEach(function (m, k) { tone(m, t + k * 0.08, 10, k ? 0.07 : 0.1, 'sine'); tone(m + 12, t + k * 0.08, 9, 0.018, 'triangle'); });
    for (var b = 0; b < 3; b++) if (Math.random() < 0.6) tone(BELL[Math.floor(Math.random() * BELL.length)], t + 1 + b * 2.2 + Math.random(), 3.5, 0.035, 'sine');
  }
  function musicLoop() {
    var want = music === 'soft' && ok && !quiet;
    if (want && !mTimer && musicGraph()) { bar(); mTimer = setInterval(function () { if (actx.state === 'running') bar(); }, 8000); }
    else if (!want && mTimer) { clearInterval(mTimer); mTimer = null; }
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden && actx && actx.resume) actx.resume(); });

  /* ---- videos ---- */
  HS.setFirst = function (src) { if (src && !first) first = src; };
  HS.playing = function () { return !!now && !now.ended && !now.error; };
  /* el: the slide; done(secs) is called once, when the slideshow should move on in secs seconds. */
  HS.play = function (el, src, poster, done) {
    var v = pool[next], n = ++seq, fin = false; next = (next + 1) % pool.length;
    v._n = n; now = v;
    function finish(secs) { if (!fin && v._n === n) { fin = true; done(secs); } }
    v.onended = function () { finish(1); };
    v.onerror = function () { finish(15); };   // can't play: the poster shows like a photo
    v.poster = poster || ''; v.muted = !soundOn(); v.src = src; el.appendChild(v); refresh();
    if (actx && actx.state !== 'running' && actx.resume) try { actx.resume(); } catch (e) {}   // a paused sound route freezes the video on iPad
    var wait = null, last = -1, still = 0, ticks = 0;
    function tapToPlay() {   // the iPad refused to start it by itself (e.g. Low Power Mode): a big ▶ starts it with a tap
      if (v._n !== n || el.querySelector('.tap')) return;
      var b = document.createElement('button'); b.className = 'tap'; b.type = 'button'; b.textContent = '▶'; el.appendChild(b);
      b.addEventListener('click', function (e) { e.stopPropagation(); clearTimeout(wait); if (b.parentNode) b.parentNode.removeChild(b); unlock(); v.muted = !soundOn(); var p3 = v.play(); if (p3 && p3.catch) p3.catch(function () { finish(3); }); });
      wait = setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); finish(1); }, 20000);
    }
    var pr = v.play();
    if (pr && pr.catch) pr.catch(function () {
      if (v._n !== n) return;
      if (!v.muted) { v.muted = true; var p2 = v.play(); if (p2 && p2.catch) p2.catch(tapToPlay); }   // sound refused: play silently
      else tapToPlay();
    });
    // watchdog: if the picture stops moving for ~10 s, nudge it once, then move on
    var dog = setInterval(function () {
      if (v._n !== n || fin) { clearInterval(dog); return; }
      if (v.paused || el.querySelector('.tap')) return;
      ticks++; if (!v.currentTime && ticks >= 23) { clearInterval(dog); finish(1); return; }   // never started in ~45 s
      if (v.readyState < 3) return;   // still downloading
      if (v.currentTime === last) { still++; if (still === 3) { if (actx && actx.resume) try { actx.resume(); } catch (e) {} if (!v.muted && actx && actx.state !== 'running') v.muted = true; try { v.play(); } catch (e) {} } if (still >= 6) { clearInterval(dog); finish(1); } }
      else { still = 0; last = v.currentTime; }
    }, 2000);
    return v;
  };
  HS.stop = function (el) {
    var v = el.querySelector('video'); if (!v) return;
    var n = v._n; v.muted = true; if (now === v) now = null; refresh();
    setTimeout(function () { if (v._n !== n) return; try { v.pause(); v.removeAttribute('src'); v.load(); } catch (e) {} if (v.parentNode) v.parentNode.removeChild(v); }, 2600);   // after the crossfade, free the memory
  };
  /* Little sound effects for the cute animations (cute.js). Silent unless the speaker button is turned up
     and the iPad has been tapped since loading; never while the night clock shows. */
  HS.chirp = function (kind) {
    if (!soundOn() || quiet) return;
    var c = ctx(); if (!c) return;
    var lvl = GAIN[vol] * 0.35, t0 = c.currentTime + 0.05;
    function blip(f1, f2, at, len, type) {
      var o = c.createOscillator(), g = c.createGain(); o.type = type || 'sine';
      o.frequency.setValueAtTime(f1, t0 + at); o.frequency.exponentialRampToValueAtTime(f2, t0 + at + len);
      g.gain.setValueAtTime(0, t0 + at); g.gain.linearRampToValueAtTime(lvl, t0 + at + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + len);
      o.connect(g); g.connect(c.destination); o.start(t0 + at); o.stop(t0 + at + len + 0.05);
    }
    if (kind === 'cuckoo') { blip(660, 650, 0, 0.32); blip(525, 515, 0.38, 0.5); }
    else if (kind === 'meow') { blip(520, 820, 0, 0.18, 'triangle'); blip(820, 430, 0.18, 0.45, 'triangle'); }
    else if (kind === 'quack') { blip(300, 220, 0, 0.14, 'square'); blip(300, 210, 0.22, 0.16, 'square'); }
    else if (kind === 'woof') { blip(780, 420, 0, 0.1, 'triangle'); blip(820, 440, 0.16, 0.12, 'triangle'); }
    else if (kind === 'pop') { blip(900, 300, 0, 0.12); }
    else if (kind === 'cheer') { [523, 659, 784, 1047, 784, 1047].forEach(function (f, i) { blip(f, f, i * 0.12, 0.3, 'triangle'); }); }
  };
  HS.setQuiet = function (q) { q = !!q; if (q !== quiet) { quiet = q; refresh(); } };

  /* ---- buttons: HomeSound.mount(box, 'big') puts 🔊 and 🎵 in the top-right of box ---- */
  var css = '.hs{position:absolute;z-index:6;display:flex;gap:10px;align-items:flex-start}' +
    '.hs .b{width:40px;height:40px;border-radius:50%;background:rgba(8,12,18,.55);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);color:#fff;font-size:19px;display:flex;align-items:center;justify-content:center;border:0;padding:0;cursor:pointer}' +
    '.hs .vol{display:none}.hs.vid .vol{display:flex}.hs .mus.on{background:rgba(243,182,73,.85)}' +
    '.hs .vol.ask{animation:hsAsk 1.6s ease-in-out infinite}@keyframes hsAsk{50%{box-shadow:0 0 0 7px rgba(243,182,73,.55)}}' +
    '.hs .menu{position:absolute;top:50px;right:0;min-width:220px;background:rgba(20,22,28,.94);border-radius:18px;padding:8px;box-shadow:0 10px 30px rgba(0,0,0,.4)}' +
    '.hs .menu[hidden]{display:none}.hs .menu a,.hs .menu button{display:flex;align-items:center;gap:10px;width:100%;box-sizing:border-box;padding:12px 14px;border:0;border-radius:12px;background:none;color:#fff;font:inherit;font-size:18px;font-weight:600;text-decoration:none;text-align:left;cursor:pointer}' +
    '.hs .menu .sel{background:rgba(243,182,73,.25)}.hs .menu .sel:after{content:"✓";margin-left:auto;color:#f3b649}.hs .menu small{display:block;font-size:13px;color:#aab3c0;font-weight:500}' +
    '.hs.big .b{width:9vmin;height:9vmin;min-width:56px;min-height:56px;font-size:max(24px,4vmin)}.hs.big{gap:2vmin}.hs.big .menu{top:calc(max(56px,9vmin) + 12px);min-width:380px}.hs.big .menu a,.hs.big .menu button{font-size:max(22px,3.4vmin);padding:2vmin 2.4vmin}.hs.big .menu small{font-size:max(15px,2.2vmin)}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  HS.mount = function (box, size) {
    var w = document.createElement('div'); w.className = 'hs' + (size ? ' ' + size : '');
    w.innerHTML = '<button class="b vol" type="button" aria-label="Video sound"></button><button class="b mus" type="button" aria-label="Background music">🎵</button>' +
      '<div class="menu" hidden><button type="button" data-m="off">🔕 關 <span>Off</span></button>' +
      '<button type="button" data-m="soft">🎵 <span>輕音樂 Soft music<small>Gentle piano-like chords</small></span></button>' +
      '<a href="spotify:" data-m="spotify">🟢 <span>Spotify<small>Opens the Spotify app</small></span></a></div>';
    box.appendChild(w);
    var u = { box: w, vol: w.querySelector('.vol'), mus: w.querySelector('.mus'), menu: w.querySelector('.menu') }; ui.push(u);
    w.addEventListener('click', function (e) { e.stopPropagation(); });   // don't open notes / change page
    u.vol.addEventListener('click', function () { vol = (vol + 1) % 4; put('vidVol', String(vol)); unlock(); refresh(); });
    u.mus.addEventListener('click', function () { u.menu.hidden = !u.menu.hidden; });
    u.menu.addEventListener('click', function (e) {
      var b = e.target.closest('[data-m]'); if (!b) return;
      music = b.getAttribute('data-m') === 'soft' ? 'soft' : 'off'; put('bgm', music);   // Spotify plays in its own app, so the page's music goes off
      u.menu.hidden = true; unlock(); refresh();
    });
    document.addEventListener('click', function () { u.menu.hidden = true; });
    refresh();
    return w;
  };
})();
