        (function () {
            /* ===== Configuración ===== */
            var CODE = "EXTRA15";          // código del cupón
            var START_H = 19;              // arranca 19 hs, termina 00 hs (hora Argentina)
            /* ?preview en la URL de la tienda (o del banner) lo muestra activo fuera de horario, para probar */
            var PREVIEW = /^https?:/.test(location.href) && /[?&#]preview\b/.test(location.href);
            try { PREVIEW = PREVIEW || /[?&#]preview\b/.test(window.top.location.href) } catch (e) { }
            if (/[?&#]preview\b/.test(document.referrer || "")) PREVIEW = true;   /* sandbox de otro origen: la URL de la tienda llega como referrer */
            /* UTM que se suma a los links de la colección (null para no agregar ninguna).
               utm_content distingue el botón "Ver productos" del clic en el fondo del banner. */
            var UTM = { utm_source: "rouge", utm_medium: "banner", utm_campaign: "happy_hour" };
            /* ID de medición de NUESTRA cuenta de Google Analytics 4 (ej. "G-AB12CD34EF").
               Vacío = no se manda a nuestra cuenta (los eventos igual quedan en el dataLayer de la tienda). */
            var GA_ID = "G-9F5G4PG0GF";
            /* Planilla de Google (Apps Script publicado como aplicación web, ver banner-happy-hour-planilla.gs).
               Cada evento se anota como una fila. Vacío = no se manda. */
            var SHEET_URL = "https://script.google.com/macros/s/AKfycbw8Ix9xltZb1A_FT5qVYbeiSB8J2DPvmInbiLdpUuJ8NvY6OGEsyytuPHkiPMO7phEn/exec";

            var $ = function (id) { return document.getElementById(id) };
            var root = $("hh");

            /* ===== Medición: eventos al dataLayer (GTM) =====
               Todos van con event "happy_hour_banner" y una "accion":
               banner_visto · raspado_iniciado · cupon_revelado · cupon_copiado · click_productos
               Dentro del iframe (sandbox con cookies) se usa el dataLayer de la tienda. */
            var T0 = Date.now(), tScratch = 0, nCopies = 0;
            function dl() {
                try { return (window.top.dataLayer = window.top.dataLayer || []) }
                catch (e) { return (window.dataLayer = window.dataLayer || []) }
            }
            /* Google Analytics propio, SIN el script gtag: el Sandbox carga el banner como otro sitio
               (sin cookies) y ahí gtag.js no arranca. Los eventos se mandan directo al mismo endpoint
               que usa gtag (google-analytics.com/g/collect), uno por acción.
               cid = visitante (se guarda en el navegador si se puede; si no, uno por carga). */
            /* OJO: el Sandbox carga el banner como página "data:", cuya dirección es TODO el HTML (~50 KB).
               Nunca usar location.href como página: los envíos quedaban gigantes y los servidores los cortaban. */
            var topUrl = "";
            try { topUrl = window.top.location.href } catch (e) { }
            if (!/^https?:/.test(topUrl)) topUrl = document.referrer || "";
            if (!/^https?:/.test(topUrl)) topUrl = "https://www.perfumeriasrouge.com/";
            topUrl = topUrl.slice(0, 300);
            function rnd() { return Math.floor(Math.random() * 2147483647) }
            var CID; try { CID = localStorage.getItem("hh_cid") } catch (e) { }
            if (!CID) { CID = rnd() + "." + Math.floor(Date.now() / 1000); try { localStorage.setItem("hh_cid", CID) } catch (e) { } }
            var SID = Math.floor(Date.now() / 1000), PAGE = rnd(), seq = 0;
            function gaSend(en, params) {
                if (!GA_ID) return;
                var q = ["v=2", "tid=" + GA_ID, "cid=" + CID, "sid=" + SID, "sct=1", "seg=1", "_p=" + PAGE, "_s=" + (++seq),
                    "dl=" + encodeURIComponent(topUrl), "dt=" + encodeURIComponent("Banner Happy Hour"),
                    "ul=" + encodeURIComponent((navigator.language || "").toLowerCase()),
                    "sr=" + screen.width + "x" + screen.height, "en=" + encodeURIComponent(en), "_et=1"];
                if (seq === 1) q.push("_ss=1");
                for (var k in params) {
                    var v = params[k];
                    q.push((typeof v === "number" ? "epn." : "ep.") + k + "=" + encodeURIComponent(v));
                }
                var qs = q.join("&");
                /* sendBeacon falla dentro del Sandbox (ERR_INSUFFICIENT_RESOURCES), así que va por fetch.
                   fetch "no-cors" se resuelve si Google respondió y falla solo si no hubo conexión:
                   en ese caso se prueba el siguiente servidor de Google (algunas redes bloquean uno). */
                /* www.google-analytics.com va último: el Service Worker de la tienda intercepta ese dominio y falla */
                var HOSTS = ["region1.google-analytics.com", "analytics.google.com", "www.google-analytics.com"];
                (function send(h) {
                    var url = "https://" + HOSTS[h] + "/g/collect?" + qs;
                    if (!window.fetch) { try { new Image().src = url } catch (e) { } return }
                    fetch(url, { method: "GET", mode: "no-cors", credentials: "omit", cache: "no-store" })
                        .catch(function () { if (h + 1 < HOSTS.length) send(h + 1) });
                })(0);
            }
            /* Planilla: un GET simple a script.google.com (los bloqueadores no lo tratan como rastreo) */
            var DEVICE = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? "celular" : "computadora";
            function sheetSend(en, params) {
                if (!SHEET_URL) return null;
                var q = ["en=" + encodeURIComponent(en), "cid=" + encodeURIComponent(CID),
                    "dispositivo=" + DEVICE, "dl=" + encodeURIComponent(topUrl), "t=" + Date.now()];
                for (var k in params) q.push(encodeURIComponent(k) + "=" + encodeURIComponent(params[k]));
                var url = SHEET_URL + (SHEET_URL.indexOf("?") < 0 ? "?" : "&") + q.join("&");
                /* keepalive: el envío sigue aunque la página cambie (clic en "Ver productos") */
                if (window.fetch) return fetch(url, { method: "GET", mode: "no-cors", credentials: "omit", cache: "no-store", keepalive: true }).catch(function () { });
                try { new Image().src = url } catch (e) { }
                return null;
            }
            function track(accion, data, done) {
                var ev = { event: "happy_hour_banner", accion: accion, cupon: CODE, estado: live ? "activo" : "antes_de_horario" };
                for (var k in data || {}) ev[k] = data[k];
                try { dl().push(ev) } catch (e) { }
                var ga = { cupon: ev.cupon, estado: ev.estado };
                for (var j in data || {}) ga[j] = data[j];
                var sent = null;
                try { sent = sheetSend(accion, ga) } catch (e) { }
                if (done) {
                    /* navegación: esperar a que la planilla reciba el evento (o 1,2 s como máximo) */
                    var fired = false, once = function () { if (!fired) { fired = true; done() } };
                    if (sent && sent.then) sent.then(once, once);
                    setTimeout(once, 1200);
                }
                try { gaSend(accion, ga) } catch (e) { }
                try { console.info("[happy hour] evento:", accion, ga) } catch (e) { }
            }
            function withUtm(url, content) {
                if (!UTM) return url;
                var q = [];
                for (var k in UTM) q.push(k + "=" + encodeURIComponent(UTM[k]));
                q.push("utm_content=" + encodeURIComponent(content));
                return url + (url.indexOf("?") < 0 ? "?" : "&") + q.join("&");
            }
            /* El banner se cuenta como visto cuando al menos la mitad aparece en pantalla, una vez por carga */
            try {
                if ("IntersectionObserver" in window) {
                    var io = new IntersectionObserver(function (en) {
                        if (en[0].isIntersecting) { io.disconnect(); track("banner_visto") }
                    }, { threshold: .5 });
                    io.observe(root);
                } else setTimeout(function () { track("banner_visto") }, 0);
            } catch (e) { }
            var LEGAL = "Válido hasta las 00 hs en productos seleccionados.";
            /* Leyenda según dispositivo: en celular se raspa con el dedo, en desktop con el mouse */
            var TOUCH = window.matchMedia && matchMedia("(hover: none) and (pointer: coarse)").matches;
            function tool() { return TOUCH ? "con el dedo" : "con el mouse" }

            /* Cinta */
            var g = "";
            for (var k = 0; k < 4; k++) ["HAPPY HOUR", "HASTA 15% OFF", "ROUGE", "PRODUCTOS SELECCIONADOS"].forEach(function (w) { g += "<span>" + w + "</span><span>✕</span>" });
            g = '<div class="hh-rgroup">' + g + "</div>";
            $("hh-rb").innerHTML = g + g;

            /* ===== Contador (hora Argentina, UTC-3) =====
               Antes del horario: cuenta hasta que empieza y el cupón está bloqueado.
               Durante el horario: cuenta hasta las 00 y el cupón se puede raspar. */
            var OFFSET = -3 * 3600000, DAY = 86400000, START = START_H * 3600;
            var last = {}, live = null;
            function pad(n) { return (n < 10 ? "0" : "") + n }
            function set(k, v) {
                if (last[k] === v) return;
                last[k] = v;
                $("hh-" + k).textContent = v;
                var box = $("hh-b" + k);
                box.classList.remove("tick");
                void box.offsetWidth;
                box.classList.add("tick");
            }
            function tick() {
                var now = Date.now(), s = Math.floor(((now + OFFSET) % DAY + DAY) % DAY / 1000);
                var isLive = PREVIEW || s >= START, left = isLive ? 86400 - s : START - s;
                if (isLive !== live) { live = isLive; setState() }
                set("h", pad(Math.floor(left / 3600)));
                set("m", pad(Math.floor(left % 3600 / 60)));
                set("s", pad(left % 60));
                setTimeout(tick, 1000 - now % 1000 + 5);
            }

            function setState() {
                $("hh-lbl").innerHTML = live ? "TERMINA EN" : "<b>EMPIEZA EN</b>";
                $("hh-timer").setAttribute("aria-label", live ? "Tiempo restante hasta las 00 hs" : "Tiempo restante hasta las " + START_H + " hs");
                cover.setAttribute("aria-disabled", live ? "false" : "true");
                cover.classList.toggle("is-live", !!live);
                if (!revealed) {
                    btn.disabled = true;
                    btnTxt.textContent = live ? "RASPÁ PARA DESBLOQUEAR" : "SE ACTIVA A LAS " + START_H + " HS";
                    legal.innerHTML = live ? "<b>Raspá el ticket " + tool() + "</b> para desbloquear tu cupón. " + LEGAL : "El cupón se desbloquea a las <b>" + START_H + " hs</b>. " + LEGAL;
                    paintCover();
                }
            }

            /* ===== Raspadita ===== */
            var cover = $("hh-cover"), cv = $("hh-canvas"), ctx = cv.getContext("2d", { willReadFrequently: true }), field = $("hh-field");
            var btn = $("hh-btn"), btnTxt = $("hh-btntxt"), legal = $("hh-legal"), codeEl = $("hh-code");
            var revealed = false, dpr = 1, W = 0, H = 0, strokes = 0;
            codeEl.textContent = CODE;   /* el código queda debajo de la raspadita y se va asomando */

            function paintCover() {
                var r = cover.getBoundingClientRect();
                dpr = window.devicePixelRatio || 1;
                W = r.width; H = r.height;
                if (!W || !H) return;
                cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.globalCompositeOperation = "source-over";
                ctx.textAlign = "center"; ctx.textBaseline = "middle";
                if (live) {
                    ctx.fillStyle = "#FF0000"; ctx.fillRect(0, 0, W, H);
                    /* acanalado del KV */
                    for (var x = 0; x < W; x += 14) {
                        ctx.fillStyle = "rgba(0,0,0,.2)"; ctx.fillRect(x, 0, 3, H);
                        ctx.fillStyle = "rgba(255,255,255,.12)"; ctx.fillRect(x + 3, 0, 2, H);
                    }
                    /* leyenda: con el dedo (mobile) / con el mouse (desktop) */
                    ctx.fillStyle = "#fff";
                    ctx.font = "800 " + (W < 240 ? 10 : 11) + "px Archivo, Arial, sans-serif";
                    if ("letterSpacing" in ctx) ctx.letterSpacing = W < 240 ? "1.5px" : "2px";
                    ctx.fillText(("✕  RASPÁ " + tool() + "  ✕").toUpperCase(), W / 2, H / 2 + 1);
                } else {
                    /* bloqueado: rayado suave */
                    ctx.fillStyle = "#f4f2ee"; ctx.fillRect(0, 0, W, H);
                    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
                    ctx.fillStyle = "rgba(0,0,0,.07)";
                    for (var d = -H; d < W + H; d += 14) {
                        ctx.beginPath(); ctx.moveTo(d, H); ctx.lineTo(d + 7, H); ctx.lineTo(d + 7 + H, 0); ctx.lineTo(d + H, 0); ctx.fill();
                    }
                    ctx.restore();
                    ctx.fillStyle = "#000";
                    ctx.font = "800 11px Archivo, Arial, sans-serif";
                    if ("letterSpacing" in ctx) ctx.letterSpacing = "2px";
                    ctx.fillText("🔒  DESDE LAS " + START_H + " HS", W / 2, H / 2 + 1);
                }
                strokes = 0;
                field.style.setProperty("--tw", Math.max(40, W * .65) + "px");
            }

            /* Pincel de moneda: sellos con borde irregular a lo largo del trazo */
            var THRESHOLD = .55, touched = false, lastBuzz = 0, lastFlake = 0;
            function stamp(x, y) {
                var r = Math.max(9, H * .3);
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
                for (var i = 0; i < 5; i++) {
                    var a = Math.random() * Math.PI * 2, d = r * (.75 + Math.random() * .45);
                    ctx.beginPath(); ctx.arc(x + Math.cos(a) * d, y + Math.sin(a) * d, 1 + Math.random() * 2.6, 0, Math.PI * 2); ctx.fill();
                }
            }
            function scratch(x0, y0, x1, y1, pType, quiet) {
                if (revealed) return;
                ctx.globalCompositeOperation = "destination-out";
                ctx.fillStyle = "#000";
                var dx = x1 - x0, dy = y1 - y0, dist = Math.sqrt(dx * dx + dy * dy), n = Math.max(1, Math.ceil(dist / 3));
                for (var i = 1; i <= n; i++) stamp(x0 + dx * i / n, y0 + dy * i / n);
                if (!touched) {
                    touched = true; field.classList.add("touched"); tScratch = Date.now();
                    track("raspado_iniciado", { metodo: pType === "touch" ? "dedo" : pType === "mouse" ? "mouse" : pType || "boton" });
                }
                var now = Date.now();
                if (now - lastFlake > 40) { lastFlake = now; flakes(x1, y1, dx) }
                if (pType === "touch" && navigator.vibrate && now - lastBuzz > 70) { lastBuzz = now; try { navigator.vibrate(4) } catch (e) { } }
                if (!quiet && ++strokes % 5 === 0) progress();
            }

            function cleared() {
                var d = ctx.getImageData(0, 0, cv.width, cv.height).data, n = 0, t = 0;
                for (var i = 3; i < d.length; i += 64) { t++; if (d[i] === 0) n++ }
                return n / t;
            }

            /* El botón muestra el avance mientras raspás */
            function progress() {
                var c = cleared();
                if (c >= THRESHOLD) return reveal();
                var pct = Math.min(99, Math.round(c / THRESHOLD * 100));
                btn.style.setProperty("--p", pct + "%");
                btnTxt.textContent = pct < 70 ? "DESBLOQUEANDO… " + pct + "%" : "¡FALTA POQUITO! " + pct + "%";
            }

            /* Virutas rojas que se desprenden y caen */
            function flakes(x, y, dir) {
                var cr = cover.getBoundingClientRect(), br = field.getBoundingClientRect();
                for (var i = 0; i < 3; i++) {
                    var f = document.createElement("i");
                    f.className = "hh-flake";
                    f.style.left = (cr.left - br.left + x) + "px";
                    f.style.top = (cr.top - br.top + y) + "px";
                    f.style.setProperty("--fx", Math.round((dir > 0 ? -1 : 1) * (6 + Math.random() * 18) + (Math.random() - .5) * 10) + "px");
                    f.style.setProperty("--fy", Math.round(18 + Math.random() * 26) + "px");
                    f.style.setProperty("--fr", Math.round(Math.random() * 360) + "deg");
                    field.appendChild(f);
                    setTimeout(function (el) { return function () { el.remove() } }(f), 750);
                }
            }

            /* "Descubrir cupón" (o Enter sobre la raspadita): la moneda raspa sola en zigzag */
            var auto = false;
            function autoScratch() {
                if (revealed || !live || auto) return;
                auto = true;
                btnTxt.textContent = "DESBLOQUEANDO…";
                var steps = 16, k = 0, px = 0, py = H * .2;
                (function step() {
                    if (revealed) return;
                    var x = (k + 1) / steps * W, y = k % 2 ? H * .15 : H * .85;
                    scratch(px, py, x, y, null, true);
                    px = x; py = y; k++;
                    if (k < steps) setTimeout(step, 28); else reveal();
                })();
            }

            function burst() {
                var b = $("hh-burst"), html = "";
                for (var i = 0; i < 14; i++) {
                    var a = i / 14 * Math.PI * 2, d = 30 + Math.random() * 26;
                    html += '<i style="--x:' + Math.round(Math.cos(a) * d * 1.9) + "px;--y:" + Math.round(Math.sin(a) * d * .8) + 'px"></i>';
                }
                b.innerHTML = html;
                setTimeout(function () { b.innerHTML = "" }, 800);
            }

            function showCopy() {
                btn.classList.add("copy");
                btnTxt.textContent = "COPIAR CUPÓN";
            }

            function reveal(silent) {
                if (revealed) return;
                revealed = true;
                codeEl.removeAttribute("aria-hidden");
                cover.classList.add("gone");
                cover.setAttribute("tabindex", "-1");
                btn.disabled = false;
                btn.classList.remove("locked");
                showCopy();
                legal.innerHTML = "<b>¡Es tuyo!</b> Ingresalo en el checkout. " + LEGAL;
                track("cupon_revelado", { metodo: auto ? "boton" : "raspado", segundos_raspando: Math.round((Date.now() - (tScratch || T0)) / 1000) });
                if (!silent) {
                    burst();
                    if (navigator.vibrate) try { navigator.vibrate([10, 40, 20]) } catch (e) { }
                    btn.classList.add("ready");
                }
            }

            /* Mouse: raspa con solo pasar por encima. Dedo: raspa arrastrando. */
            var down = false, lx = null, ly = null;
            function pos(e) { var r = cover.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top] }
            cover.addEventListener("pointerdown", function (e) {
                if (!live || revealed || auto) return;
                if (e.pointerType === "touch" && !TOUCH && !touched) { TOUCH = true; setState(); }
                down = true;
                var p = pos(e); lx = p[0]; ly = p[1];
                scratch(lx, ly, lx, ly, e.pointerType);
                try { cover.setPointerCapture(e.pointerId) } catch (err) { }
            });
            cover.addEventListener("pointermove", function (e) {
                if (!live || revealed || auto) return;
                if (!down && e.pointerType !== "mouse") return;
                var p = pos(e);
                if (lx === null) { lx = p[0]; ly = p[1] }
                scratch(lx, ly, p[0], p[1], e.pointerType);
                lx = p[0]; ly = p[1];
            });
            function up() { down = false; if (!revealed && live && touched && !auto) progress() }
            cover.addEventListener("pointerup", up);
            cover.addEventListener("pointercancel", up);
            cover.addEventListener("pointerleave", function () { lx = ly = null; up() });
            cover.addEventListener("click", function (e) { if (e.detail === 0) autoScratch() });

            /* ===== Botón: descubrir / copiar ===== */
            function fallbackCopy(txt) {
                var ta = document.createElement("textarea");
                ta.value = txt; ta.setAttribute("readonly", "");
                ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
                document.body.appendChild(ta); ta.select();
                var ok = false;
                try { ok = document.execCommand("copy") } catch (e) { }
                document.body.removeChild(ta);
                return ok;
            }
            function copied(ok) {
                track("cupon_copiado", { copiado: ok ? "si" : "no", vez: ++nCopies });
                btn.classList.remove("ready");
                btn.classList.add("done");
                btnTxt.textContent = ok ? "¡COPIADO!" : "COPIALO A MANO";
                legal.innerHTML = ok ? "Cupón <b>" + CODE + "</b> copiado. Pegalo en el checkout antes de las <b>00 hs</b>."
                    : "Seleccioná el código y copialo. " + LEGAL;
                if (!ok) {
                    var r = document.createRange(); r.selectNodeContents(codeEl);
                    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
                }
                clearTimeout(copied.t);
                copied.t = setTimeout(function () { btn.classList.remove("done"); showCopy() }, 2200);
            }
            btn.addEventListener("click", function () {
                if (!revealed) return;
                /* dentro del Sandbox el portapapeles puede estar bloqueado: cualquier falla cae al método viejo */
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
                        var answered = false;
                        navigator.clipboard.writeText(CODE).then(function () { if (!answered) { answered = true; copied(true) } },
                            function () { if (!answered) { answered = true; copied(fallbackCopy(CODE)) } });
                        /* si el navegador nunca responde, igual se registra el intento */
                        setTimeout(function () { if (!answered) { answered = true; copied(fallbackCopy(CODE)) } }, 1500);
                        return;
                    }
                } catch (e) { }
                copied(fallbackCopy(CODE));
            });

            /* ===== Navegación =====
               El fondo del banner lleva a la colección; la tarjeta del cupón no navega.
               El banner vive en un iframe: se navega la página de arriba. */
            function go(href) { try { window.top.location.href = href } catch (err) { window.location.href = href } }
            root.addEventListener("click", function (e) {
                if (e.target.closest("#hh-card")) return;
                e.preventDefault();
                var a = e.target.closest("a"), origen = a ? "boton_ver_productos" : "fondo_banner";
                var href = a ? a.href : withUtm(root.getAttribute("data-href"), origen);
                track("click_productos", { origen: origen, cupon_revelado: revealed ? "si" : "no" }, function () { go(href) });
            });

            /* Arranque */
            $("hh-more").href = withUtm($("hh-more").href, "boton_ver_productos");   /* también sirve si lo abren en otra pestaña */
            tick();
            var rt;
            window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { if (!revealed) paintCover() }, 150) });
            if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { if (!revealed) paintCover() });
        })();
