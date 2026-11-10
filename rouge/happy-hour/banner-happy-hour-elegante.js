        (function () {
            /* ===== Configuración ===== */
            var CODE = "EXTRA15";          // código del cupón
            var START_H = 18;              // arranca 18 hs, termina 00 hs (hora Argentina)
            /* ?preview en la URL de la tienda (o del banner) lo muestra activo fuera de horario, para probar */
            var PREVIEW = /^https?:/.test(location.href) && /[?&#]preview\b/.test(location.href);
            try { PREVIEW = PREVIEW || /[?&#]preview\b/.test(window.top.location.href) } catch (e) { }
            if (/[?&#]preview\b/.test(document.referrer || "")) PREVIEW = true;   /* sandbox de otro origen: la URL de la tienda llega como referrer */
            /* ?bomba hace lo contrario: muestra el banner Bomba aunque sea horario de Happy Hour */
            var BOMBA = /^https?:/.test(location.href) && /[?&#]bomba\b/.test(location.href);
            try { BOMBA = BOMBA || /[?&#]bomba\b/.test(window.top.location.href) } catch (e) { }
            if (/[?&#]bomba\b/.test(document.referrer || "")) BOMBA = true;
            if (BOMBA) PREVIEW = false;
            /* UTM que se suma a los links de la colección (null para no agregar ninguna).
               utm_content distingue el botón "Ver productos" del clic en el fondo del banner. */
            var UTM = { utm_source: "rouge", utm_medium: "banner", utm_campaign: "happy_hour", utm_term: "elegante" };
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
                    "dl=" + encodeURIComponent(topUrl), "dt=" + encodeURIComponent("Banner Happy Hour Elegante"),
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
                var ev = { event: "happy_hour_banner", accion: accion, cupon: CODE, version: "elegante", estado: live ? "activo" : "antes_de_horario" };
                for (var k in data || {}) ev[k] = data[k];
                try { dl().push(ev) } catch (e) { }
                var ga = { cupon: ev.cupon, version: ev.version, estado: ev.estado };
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

            /* ===== Contador (hora Argentina, UTC-3) =====
               De 00 a 18 hs se muestra el banner Bomba (#bk) y el Happy Hour queda oculto.
               De 18 a 00 hs se muestra el Happy Hour: cuenta hasta las 00 y el código se puede copiar.
               El cambio pasa solo, aunque la página quede abierta. */
            var OFFSET = -3 * 3600000, DAY = 86400000, START = START_H * 3600;
            var last = {}, live = null, nCopies = 0;
            var btn = $("hh-btn"), legal = $("hh-legal"), codeEl = $("hh-code");
            var LEGAL_ON = "Acumulable con cualquier promoción · Válido de " + START_H + " a 00 hs";
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
            function setState() {
                var bomba = $("bk");
                if (bomba) bomba.hidden = !!live;
                root.hidden = !live;
                $("hh-lbl").textContent = live ? "Finaliza en" : "Empieza en";
                $("hh-timer").setAttribute("aria-label", live ? "Tiempo restante hasta las 00 hs" : "Tiempo restante hasta las " + START_H + " hs");
                codeEl.textContent = live ? CODE : "• • • • • • •";
                codeEl.classList.toggle("locked", !live);
                codeEl.setAttribute("aria-label", live ? "Código " + CODE : "El código se revela a las " + START_H + " hs");
                btn.disabled = !live;
                btn.classList.remove("done");
                btn.textContent = live ? "COPIAR CÓDIGO" : "DISPONIBLE A LAS " + START_H + " HS";
                legal.innerHTML = live ? LEGAL_ON : "El código se revela a las <b>" + START_H + " hs</b> · Acumulable con cualquier promoción";
            }
            function tick() {
                var now = Date.now(), s = Math.floor(((now + OFFSET) % DAY + DAY) % DAY / 1000);
                var isLive = !BOMBA && (PREVIEW || s >= START), left = isLive ? 86400 - s : START - s;
                if (isLive !== live) { live = isLive; setState() }
                set("h", pad(Math.floor(left / 3600)));
                set("m", pad(Math.floor(left % 3600 / 60)));
                set("s", pad(left % 60));
                setTimeout(tick, 1000 - now % 1000 + 5);
            }

            /* ===== Copiar código ===== */
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
                btn.classList.add("done");
                btn.textContent = ok ? "¡COPIADO!" : "COPIALO A MANO";
                legal.innerHTML = ok ? "Código <b>" + CODE + "</b> copiado. Pegalo en el checkout: se suma a cualquier promoción."
                    : "Seleccioná el código y copialo. " + LEGAL_ON;
                if (!ok) {
                    var r = document.createRange(); r.selectNodeContents(codeEl);
                    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
                }
                clearTimeout(copied.t);
                copied.t = setTimeout(function () {
                    if (!live) return;
                    btn.classList.remove("done"); btn.textContent = "COPIAR CÓDIGO"; legal.innerHTML = LEGAL_ON;
                }, 2200);
            }
            btn.addEventListener("click", function () {
                if (!live) return;
                /* dentro del Sandbox el portapapeles puede estar bloqueado: cualquier falla cae al método viejo */
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
                        var answered = false;
                        navigator.clipboard.writeText(CODE).then(function () { if (!answered) { answered = true; copied(true) } },
                            function () { if (!answered) { answered = true; copied(fallbackCopy(CODE)) } });
                        setTimeout(function () { if (!answered) { answered = true; copied(fallbackCopy(CODE)) } }, 1500);
                        return;
                    }
                } catch (e) { }
                copied(fallbackCopy(CODE));
            });

            /* ===== Navegación =====
               El fondo del banner lleva a la colección; la tarjeta del código no navega.
               El banner vive en un iframe: se navega la página de arriba. */
            function go(href) { try { window.top.location.href = href } catch (err) { window.location.href = href } }
            root.addEventListener("click", function (e) {
                if (e.target.closest("#hh-card")) return;
                e.preventDefault();
                var a = e.target.closest("a"), origen = a ? "boton_ver_productos" : "fondo_banner";
                var href = a ? a.href : withUtm(root.getAttribute("data-href"), origen);
                track("click_productos", { origen: origen }, function () { go(href) });
            });

            /* Arranque */
            $("hh-more").href = withUtm($("hh-more").href, "boton_ver_productos");
            tick();
        })();

        /* ===================================================================
           BANNER BOMBA (de 00 a 18 hs). Copiado de rouge/banners/banner-bomba-kv.html.
           =================================================================== */
        (function () {
            /* Cintas */
            function group(words) {
                var a = "";
                for (var k = 0; k < 4; k++) words.forEach(function (w) { a += "<span>" + w + "</span><span>✕</span>" });
                return '<div class="bk-rgroup">' + a + "</div>";
            }
            var ga = group(["OFERTAS BOMBA", "ROUGE", "SOLO POR HOY"]), gb = group(["OFERTAS BOMBA", "HASTA 65% OFF", "ROUGE"]);
            document.getElementById("bk-ra").innerHTML = ga + ga;
            document.getElementById("bk-rb").innerHTML = gb + gb;

            /* Contador hasta las 00 hs de Argentina (UTC-3); a medianoche vuelve a arrancar desde 24 hs */
            var OFFSET = -3 * 3600000, DAY = 86400000;
            var el = {
                h: document.getElementById("bk-h"), m: document.getElementById("bk-m"), s: document.getElementById("bk-s"),
                bh: document.getElementById("bk-bh"), bm: document.getElementById("bk-bm"), bs: document.getElementById("bk-bs"),
                burnt: document.getElementById("bk-burnt"), spark: document.getElementById("bk-fspark")
            };
            var last = {};
            function pad(n) { return (n < 10 ? "0" : "") + n }
            function set(k, box, v) {
                if (last[k] === v) return;
                last[k] = v;
                el[k].textContent = v;
                el[box].classList.remove("tick");
                void el[box].offsetWidth;
                el[box].classList.add("tick");
            }
            function tick() {
                var now = Date.now(), left = Math.ceil((DAY - (now + OFFSET) % DAY) / 1000) % 86400;
                set("h", "bh", pad(Math.floor(left / 3600)));
                set("m", "bm", pad(Math.floor(left % 3600 / 60)));
                set("s", "bs", pad(left % 60));
                /* La chispa avanza de derecha a izquierda: lo que queda de mecha = lo que queda del día */
                var pct = (left / 86400) * 100;
                el.spark.style.left = pct + "%";
                el.burnt.style.width = (100 - pct) + "%";
                setTimeout(tick, 1000 - now % 1000 + 5);
            }
            tick();

            /* El banner vive en un iframe: se navega la página de arriba */
            var a = document.getElementById("bk");
            a.addEventListener("click", function (e) {
                e.preventDefault();
                try { window.top.location.href = a.href } catch (err) { window.location.href = a.href }
            });
        })();
