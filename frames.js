/* Photo frames for the slideshows (index.html and parents/index.html).
   Pure CSS drawn over the photo at show time; the photo files are never changed.
   Each photo always gets the same frame (picked from its file name), so the slideshow
   mixes polaroid, wood, film, gold, washi tape and plain. In December some photos get a
   candy-cane frame, around Chinese New Year a red-and-gold 福 frame.
   Turn off on one iPad with ?frames=0 in the address (remembered). */
(function () {
  var css =
    '.frm{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;box-sizing:border-box;border:0 solid transparent;opacity:0;transition:opacity 1.2s ease;font-size:16px}' +
    '.frm.on{opacity:1}' +
    '.frm:before,.frm:after{content:"";position:absolute}' +
    /* polaroid: cream card, deep bottom edge */
    '.frm.f-polaroid{border-width:.9em .9em 2.8em;border-color:#f6f2e8;box-shadow:inset 0 0 0 1px rgba(0,0,0,.18),inset 0 .15em .6em rgba(0,0,0,.35)}' +
    /* wood: grain stripes with a dark inner lip */
    '.frm.f-wood{border-width:1.1em;border-image:repeating-linear-gradient(83deg,#6f4524 0,#82552e .35em,#5d391c .55em,#7a4f2b .9em,#6a4222 1.2em) 1;box-shadow:inset 0 0 0 .18em #3b2412,inset 0 .2em .7em rgba(0,0,0,.5)}' +
    /* film strip: black bands with sprocket holes */
    '.frm.f-film{border-width:1.5em .45em;border-color:#111}' +
    '.frm.f-film:before,.frm.f-film:after{left:0;right:0;height:.55em;background:repeating-linear-gradient(90deg,transparent 0,transparent .6em,#e9e4d8 .6em,#e9e4d8 1.25em,transparent 1.25em,transparent 1.85em);border-radius:2px}' +
    '.frm.f-film:before{top:-1.02em}.frm.f-film:after{bottom:-1.02em}' +
    /* gold: gilded bevel with a thin inner line */
    '.frm.f-gold{border-width:1em;border-image:linear-gradient(135deg,#8a6a1f,#f4dc8a 22%,#a47c2a 45%,#f7e7a6 68%,#8a6a1f) 1;box-shadow:inset 0 0 0 .2em rgba(60,40,5,.55),inset 0 0 0 .32em #e9cf7f}' +
    /* washi tape: two strips of tape on the corners, no border */
    '.frm.f-tape:before,.frm.f-tape:after{width:6.5em;height:1.6em;opacity:.92;box-shadow:0 1px 3px rgba(0,0,0,.25)}' +
    '.frm.f-tape:before{top:1.3em;left:-.9em;transform:rotate(-38deg);background:repeating-linear-gradient(45deg,#f6a5c0 0,#f6a5c0 .45em,#fde3ec .45em,#fde3ec .9em)}' +
    '.frm.f-tape:after{bottom:1.3em;right:-.9em;transform:rotate(-38deg);background:repeating-linear-gradient(45deg,#8fd0c9 0,#8fd0c9 .45em,#e2f5f2 .45em,#e2f5f2 .9em)}' +
    /* Christmas: candy-cane stripes */
    '.frm.f-xmas{border-width:.85em;border-image:repeating-linear-gradient(45deg,#c8102e 0,#c8102e .6em,#fff .6em,#fff 1.2em,#1f7a3a 1.2em,#1f7a3a 1.8em,#fff 1.8em,#fff 2.4em) 1;box-shadow:inset 0 .15em .6em rgba(0,0,0,.4)}' +
    /* Chinese New Year: red with a gold line and a 福 corner */
    '.frm.f-cny{border-width:1em;border-color:#b3121b;box-shadow:inset 0 0 0 .2em #e8c25a,inset 0 .2em .8em rgba(0,0,0,.4)}' +
    '.frm.f-cny:before{content:"福";top:-.6em;right:-.6em;width:2.4em;height:2.4em;line-height:2.4em;text-align:center;font-size:1.1em;font-weight:700;color:#b3121b;background:#f2cd5c;transform:rotate(45deg);border-radius:.3em;box-shadow:0 2px 6px rgba(0,0,0,.35)}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var off = false;
  try {
    var m = /[?&]frames=(\d)/.exec(location.search);
    if (m) localStorage.setItem('frames', m[1]);
    off = localStorage.getItem('frames') === '0';
  } catch (e) {}

  var BASE = ['polaroid', 'wood', 'film', 'gold', 'tape', 'plain'];
  function festive() {
    var d = new Date(), mo = d.getMonth() + 1, day = d.getDate();
    if (mo === 12) return 'xmas';
    if ((mo === 1 && day >= 20) || (mo === 2 && day <= 20)) return 'cny';   // around Chinese New Year
    return '';
  }
  function hash(s) { var h = 7; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 100003; return h; }
  function pick(src) {
    var h = hash(String(src || '')), f = festive();
    if (f && h % 3 === 0) return f;   // a third of the photos in season
    return BASE[h % BASE.length];
  }

  window.PhotoFrames = {
    pick: pick,
    // Make the frame layer. "before": the element it goes in front of (inside "box").
    mount: function (box, before, size) {
      var f = document.createElement('div'); f.className = 'frm';
      if (size) f.style.fontSize = size;
      box.insertBefore(f, before || null);
      return f;
    },
    /* Show the frame for photo "src". With "fit" (the photo is shown with background-size: contain),
       the frame hugs the photo itself rather than the screen edges. */
    show: function (f, src, fit) {
      var n = f._n = (f._n || 0) + 1;
      f.className = 'frm'; f.parentNode.removeAttribute('data-frame');
      if (off || !src) return;
      var name = window.PhotoFrames.pick(src);
      if (name === 'plain') return;
      f.parentNode.setAttribute('data-frame', name);   // pages nudge their captions inside the frame
      function on() { if (f._n !== n) return; f.className = 'frm f-' + name; setTimeout(function () { if (f._n === n) f.className = 'frm f-' + name + ' on'; }, 30); }
      if (!fit) { setTimeout(on, 600); return; }
      var img = new Image();
      img.onload = function () {
        if (f._n !== n) return;
        var p = f.parentNode, W = p.clientWidth, H = p.clientHeight, s = Math.min(W / img.width, H / img.height);
        var w = Math.round(img.width * s), h = Math.round(img.height * s);
        f.style.left = Math.round((W - w) / 2) + 'px'; f.style.top = Math.round((H - h) / 2) + 'px';
        f.style.right = 'auto'; f.style.bottom = 'auto'; f.style.width = w + 'px'; f.style.height = h + 'px';
        setTimeout(on, 2600);   // once the photo has settled into place
      };
      img.src = src;
    }
  };
})();
