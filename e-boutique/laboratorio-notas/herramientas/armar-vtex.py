r"""Genera la versión del laboratorio para el tema de VTEX IO (bloque `laboratorio-notas` de Rouge-VTEX-theme)
a partir de arma-perfume-notas.html, igual que armar-sandbox.py genera la del Sandbox.

Escribe en el tema (página /laboratorio-notas, bloque `laboratorio-notas`):
  react/components/laboratorio-notas/motor.js    el laboratorio (runtime + lógica) como función montarLaboratorio()
  react/components/laboratorio-notas/catalogo.js el catálogo (copia de catalogo.json)
  react/components/laboratorio-notas/estilos.ts  el CSS, encerrado en .rouge-lab para no pisar estilos de la tienda

Uso (desde la carpeta laboratorio-notas):
  python herramientas/armar-vtex.py                       (busca el tema en ../../../Rouge-VTEX-theme)
  python herramientas/armar-vtex.py C:\ruta\al\tema
Se edita siempre arma-perfume-notas.html y después se vuelve a correr esto."""
import os, re, sys

aqui = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(aqui, '..', 'arma-perfume-notas.html')
TEMA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(aqui, '..', '..', '..', '..', 'Rouge-VTEX-theme')
DEST = os.path.join(TEMA, 'react', 'components', 'laboratorio-notas')
if not os.path.isfile(os.path.join(TEMA, 'manifest.json')):
    raise SystemExit('No encuentro el tema en ' + os.path.abspath(TEMA))

html = open(SRC, encoding='utf-8').read()
sin_comentarios = re.sub(r'<!--.*?-->', '', html, flags=re.S)
scripts = re.findall(r'<script>(.*?)</script>', sin_comentarios, re.S)
if len(scripts) != 2:
    raise SystemExit('Esperaba 2 bloques <script>, encontré %d' % len(scripts))
css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)


def cambiar(texto, viejo, nuevo, veces=1):
    n = texto.count(viejo)
    if n != veces:
        raise SystemExit('No pude adaptar el código (%d coincidencias en vez de %d):\n  %s' % (n, veces, viejo[:120]))
    return texto.replace(viejo, nuevo)


def escribir(ruta, texto):
    """solo si cambió: con "vtex link" corriendo, reenviar el catálogo (600 KB) sin cambios hace que VTEX lo rechace (413)"""
    if os.path.isfile(ruta) and open(ruta, encoding='utf-8', newline='').read() == texto:
        return
    open(ruta, 'w', encoding='utf-8', newline='\n').write(texto)


def sin_comentarios(js):
    """el código que va al tema no lleva comentarios: los saca el TypeScript del propio tema"""
    import subprocess
    ts = os.path.join(TEMA, 'node_modules', 'typescript')
    prog = ("const ts=require(process.argv[1]);let s='';process.stdin.setEncoding('utf8');"
            "process.stdin.on('data',d=>s+=d).on('end',()=>process.stdout.write(ts.transpileModule(s,"
            "{compilerOptions:{removeComments:true,target:ts.ScriptTarget.ESNext,module:ts.ModuleKind.ESNext}}).outputText))")
    r = subprocess.run(['node', '-e', prog, ts], input=js.encode('utf-8'), capture_output=True, check=True)
    return r.stdout.decode('utf-8')


# ---------- JS ----------
runtime, logica = scripts

# morphdom viene como UMD (module.exports / define): dentro de un módulo de webpack se usa como variable local
runtime = cambiar(runtime,
                  '(function (global, factory) { typeof exports === "object" && typeof module !== "undefined" ? module.exports = factory() : typeof define === "function" && define.amd ? define(factory) : (global = global || self, global.morphdom = factory()) })(this, function () {',
                  'var morphdom = (function () {')
runtime = cambiar(runtime, 'var morphdom = morphdomFactory(morphAttrs); return morphdom });',
                  'var morphdom = morphdomFactory(morphAttrs); return morphdom })();')

# Agregar al carrito de verdad (vtex.order-items) en lugar de ir al checkout; el texto del botón muestra el estado
logica = cambiar(logica, '<a class="btn" href="{{res.cartUrl}}" data-track="agregar_carrito" data-name="{{res.house}} {{res.name}}" style="background: {{accent}}; color: #F3ECE3">Agregar al carrito</a>',
                 '<button class="btn" type="button" onClick="{{res.addCart}}" aria-live="polite" style="background: {{accent}}; color: #F3ECE3">{{res.cartText}}</button>')
logica = cambiar(logica, "                    o.cartUrl = pr.sku ?", """                    o.cartText = st.cartMsg && st.cartFor === pr.sku ? st.cartMsg : 'Agregar al carrito';
                    o.addCart = function () {
                        if (!AP.agregar || !pr.sku || self.state.cartMsg === 'Agregando…') return;
                        AP.track('agregar_carrito', { perfume: x.p.house + ' ' + x.p.name });
                        self.setState({ cartMsg: 'Agregando…', cartFor: pr.sku });
                        Promise.resolve(AP.agregar({ sku: String(pr.sku), seller: String(pr.seller || 1), price: pr.price, list: pr.list, size: pr.size, p: x.p }))
                            .then(function (ok) { self.setState({ cartMsg: ok === false ? 'No se pudo agregar' : '¡Agregado al carrito!' }); },
                                function () { self.setState({ cartMsg: 'No se pudo agregar' }); })
                            .then(function () { clearTimeout(self.cmT); self.cmT = setTimeout(function () { self.setState({ cartMsg: '' }); }, 2600); });
                    };
                    o.cartUrl = pr.sku ?""")

# Montaje: en la tienda no hay iframe; las imágenes y el carrito llegan por parámetro
logica = cambiar(logica, "        var app = document.getElementById('app');", '        var app = root;')
logica = re.sub(r"        // Imágenes: en la compu.*?app\.textContent = [^\n]*\n        \}\);",
                """        // Dentro de la tienda: API de VTEX del mismo dominio (precio y stock en vivo) y carrito real
        AP.origin = function () { return location.origin; };
        AP.PRECIOS_URL = '';
        AP.LISTA_URL = 'https://ebeusd.github.io/videos-difu/e-boutique/laboratorio-notas/precios.json';
        AP.CARRITO = true;
        AP.agregar = opciones.agregar;
        AP.img = opciones.img;
        AP.P = opciones.catalogo;
        AP.MARCAS = opciones.marcas || [];
        AP.FUERZA = opciones.fuerza || 'media';
        AP.EXCLUIR = opciones.excluir || [];
        AP.ORDEN = opciones.orden || null;
        AP.MODO = opciones.modo || 'lab';
        var inst = mountDC(Component, { "accent": opciones.accent || "#730101", "imgBase": '', "frascoBase": '' }, tpl, app);""",
                logica, count=1, flags=re.S)
if 'opciones.agregar' not in logica:
    raise SystemExit('No pude adaptar el montaje del laboratorio')
# Imágenes: las resuelve el componente con los assets del tema
logica = cambiar(logica, 'n.img = IMG + n.f;', "n.img = AP.img('notas', n.f);")
logica = cambiar(logica, "var BOTTLE = { glass: FRASCO + 'frasco-vidrio.webp', cap: FRASCO + 'frasco-tapa.webp' };",
                 "var BOTTLE = { glass: AP.img('frasco', 'frasco-vidrio.webp'), cap: AP.img('frasco', 'frasco-tapa.webp') };")
logica = cambiar(logica, '        // Links fuera del iframe de VTEX', '        // Links (ficha del producto): se registra el evento y se navega')
logica = cambiar(logica, '            try { window.top.location.href = a.href; } catch (err) { window.location.href = a.href; }',
                 '            window.location.href = a.href;')
logica = logica.rstrip() + '\n        return inst;\n'

# El catálogo va en su propio archivo: el componente lo importa aparte (import dinámico) y lo pasa al montar
import json
catalogo = json.load(open(os.path.join(aqui, '..', 'catalogo.json'), encoding='utf-8'))
os.makedirs(DEST, exist_ok=True)
escribir(os.path.join(DEST, 'catalogo.js'),
    'export const CATALOGO = ' + json.dumps(catalogo, ensure_ascii=False, separators=(',', ':')) + '\n')
# Marcas del catálogo: las opciones del desplegable "Marcas a destacar" del Site Editor
marcas = sorted({p['house'] for p in catalogo}, key=lambda m: m.lower())
cita = lambda m: '"%s"' % m if "'" in m else "'%s'" % m
escribir(os.path.join(DEST, 'marcas.ts'), 'export const MARCAS = [\n' + ''.join('  %s,\n' % cita(m) for m in marcas) + ']\n')

motor = (
         'export function montarLaboratorio(root, opciones) {\n'
         + runtime + '\n' + logica +
         '}\n')
os.makedirs(DEST, exist_ok=True)
motor = sin_comentarios(motor)
escribir(os.path.join(DEST, 'motor.js'), motor)


# ---------- CSS: todo bajo .rouge-lab y animaciones con prefijo ap- ----------
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
anims = re.findall(r'@keyframes\s+([\w-]+)', css)


def anim(decl):
    # renombra solo dentro de animation / animation-name
    def r(m):
        v = m.group(2)
        for a in anims:
            v = re.sub(r'(?<![\w-])%s(?![\w-])' % re.escape(a), 'ap-' + a, v)
        return m.group(1) + v
    return re.sub(r'(animation(?:-name)?\s*:)([^;}]*)', r, decl)


def selector(s):
    s = s.strip()
    if s in ('body', 'html'):
        return '.rouge-lab'
    return '.rouge-lab ' + s


def scope(bloque):
    out, i = [], 0
    while i < len(bloque):
        j = bloque.find('{', i)
        if j < 0:
            break
        cabeza = bloque[i:j].strip()
        # buscar la llave que cierra (con anidamiento)
        prof, k = 1, j + 1
        while prof:
            prof += {'{': 1, '}': -1}.get(bloque[k], 0)
            k += 1
        cuerpo = bloque[j + 1:k - 1]
        if cabeza.startswith('@keyframes'):
            nombre = cabeza.split()[1]
            out.append('@keyframes ap-%s{%s}' % (nombre, cuerpo.strip()))
        elif cabeza.startswith('@media') or cabeza.startswith('@supports'):
            out.append('%s{%s}' % (cabeza, scope(cuerpo)))
        else:
            cuerpo = anim(cuerpo.strip())
            if cabeza in ('body', 'html'):
                cuerpo = re.sub(r'margin\s*:\s*0\s*;?', '', cuerpo)
            out.append('%s{%s}' % (','.join(selector(s) for s in cabeza.split(',')), cuerpo))
        i = k
    return '\n'.join(out)


css_ok = scope(css)
# En la tienda el laboratorio no ocupa la pantalla fija (eso era para el iframe del Sandbox):
# toma la altura de su contenido y la página scrollea normal. En celular la barra de abajo queda pegada al borde.
css_ok += '''
.rouge-lab .ap{height:auto;min-height:0;overflow:visible}
.rouge-lab .ap-intro-pyr,.rouge-lab .ap-intro-txt{height:auto;max-height:none;overflow:visible}
.rouge-lab .ap-body,.rouge-lab .ap-res,.rouge-lab .ap-mixing{flex:none}
@media (max-width: 899px){
.rouge-lab .ap-main,.rouge-lab .ap-side{flex:none}
.rouge-lab .ap-bar{position:sticky;bottom:0;z-index:5}}'''
# la fuente se carga desde el componente (los @import dentro de un <style> en el body no siempre se respetan)
import json
estilos = ('export const ESTILOS = ' + json.dumps(css_ok, ensure_ascii=False) + '\n')
escribir(os.path.join(DEST, 'estilos.ts'), estilos)

# ---------- Imágenes en assets/ del tema + bloque con el mapa de imágenes ----------
# El builder "store" convierte cada "assets/..." de las props en la URL publicada (también dentro de objetos).
import shutil
IMGS = os.path.join(aqui, '..', 'imagenes')
mapa = {}
for tipo in ('notas', 'frasco'):
    destino = os.path.join(TEMA, 'assets', 'laboratorio-notas', tipo)
    os.makedirs(destino, exist_ok=True)
    mapa[tipo] = {}
    for f in sorted(os.listdir(os.path.join(IMGS, tipo))):
        # solo las que usa el laboratorio (en la carpeta puede haber otras, como banners)
        if f.lower().endswith('.webp') and "'%s'" % f in html:
            o, d = os.path.join(IMGS, tipo, f), os.path.join(destino, f)
            # solo si cambió: con "vtex link" corriendo, recopiar todo reenvía las 53 imágenes y VTEX lo rechaza (413)
            if not os.path.isfile(d) or open(o, 'rb').read() != open(d, 'rb').read():
                shutil.copyfile(o, d)
            mapa[tipo][f] = 'assets/laboratorio-notas/%s/%s' % (tipo, f)
    for f in os.listdir(destino):
        if f not in mapa[tipo]:
            os.remove(os.path.join(destino, f))
# Página: carpeta "disposition-layout" donde, desde el Site Editor, se prende cada parte y se elige el orden
BANNER_EJEMPLO = {
    'image': 'https://rougeb2car.vtexassets.com/assets/vtex.file-manager-graphql/images/b1485bc9-cec6-4eea-a649-9c34cbaefb4a___b8f6c8360adb472e12ff4ea9b57702eb.webp',
    'mobileImage': 'https://rougeb2car.vtexassets.com/assets/vtex.file-manager-graphql/images/c2257df9-4b1c-483d-91a4-20cda7839a81___e080c76f2b9105787adb291a8e6085ea.webp',
}


def sandbox(n):
    return {
        'toggle-layout#laboratorio-notas-sandbox-%d' % n: {
            'title': '[%d] [On/Off] Sandbox %d' % (n + 1, n),
            'children': ['sandbox#laboratorio-notas-%d' % n],
            'props': {'renderChildren': False},
        },
        'sandbox#laboratorio-notas-%d' % n: {
            'title': 'Sandbox %d contenido' % n,
            'props': {'width': '100%', 'height': 'auto', 'initialContent': '', 'allowCookies': True},
        },
    }


partes = ['toggle-layout#laboratorio-notas-banner', 'toggle-layout#laboratorio-notas-sandbox-1',
          'toggle-layout#laboratorio-notas-sandbox-2', 'toggle-layout#laboratorio-notas-componente',
          'toggle-layout#laboratorio-notas-capas']
bloque = {
    'store.custom#laboratorio-notas': {
        'blocks': ['disposition-layout#laboratorio-notas'],
    },
    'disposition-layout#laboratorio-notas': {
        'title': 'Laboratorio de notas / Contenido',
        'children': partes,
        'props': {'disposition': [{'order': i + 1} for i in range(len(partes))]},
    },
    'toggle-layout#laboratorio-notas-banner': {
        'title': '[1] [On/Off] Banner',
        'children': ['list-context.image-list#laboratorio-notas-banner'],
        'props': {'renderChildren': True},
    },
    'list-context.image-list#laboratorio-notas-banner': {
        'title': 'Imágenes del banner (Desktop/Mobile)',
        'children': ['slider-layout#laboratorio-notas-banner'],
        'props': {'height': 'auto', 'images': [BANNER_EJEMPLO]},
    },
    'slider-layout#laboratorio-notas-banner': {
        'props': {
            'itemsPerPage': {'desktop': 1, 'tablet': 1, 'phone': 1},
            'fullWidth': True,
            'infinite': True,
            'showNavigationArrows': 'desktopOnly',
            'showPaginationDots': 'always',
            'autoplay': {'timeout': 5000, 'stopOnHover': True},
            'blockClass': 'laboratorio-notas-banner',
        },
    },
    **sandbox(1),
    **sandbox(2),
    'toggle-layout#laboratorio-notas-componente': {
        'title': '[4] [On/Off] Laboratorio de notas',
        'children': ['laboratorio-notas'],
        'props': {'renderChildren': True},
    },
    'laboratorio-notas': {
        'title': 'Laboratorio de notas',
        'props': {'archivos': mapa},
    },
    'toggle-layout#laboratorio-notas-capas': {
        'title': '[5] [On/Off] Capas del perfume',
        'children': ['laboratorio-notas-capas'],
        'props': {'renderChildren': True},
    },
    'laboratorio-notas-capas': {
        'title': 'Capas del perfume (salida, corazón y fondo)',
        'props': {'archivos': mapa},
    },
}
jsonc = (json.dumps(bloque, ensure_ascii=False, indent=2) + '\n')
escribir(os.path.join(TEMA, 'store', 'blocks', 'laboratorio-notas.jsonc'), jsonc)
# versión anterior: bloque dentro de new-home
viejo = os.path.join(TEMA, 'store', 'blocks', 'newHome', 'blocks-new-home', 'LaboratorioNotas.jsonc')
if os.path.isfile(viejo):
    os.remove(viejo)

# ruta /laboratorio-notas
rutas_f = os.path.join(TEMA, 'store', 'routes.json')
rutas = open(rutas_f, encoding='utf-8', newline='').read()
if '"store.custom#laboratorio-notas"' not in rutas:
    eol = '\r\n' if '\r\n' in rutas else '\n'
    fin = rutas.rstrip().rindex('}')
    rutas = (rutas[:fin].rstrip() + ',' + eol + eol + '  "store.custom#laboratorio-notas": {' + eol
             + '    "path": "/laboratorio-notas"' + eol + '  }' + eol + '}' + eol)
    open(rutas_f, 'w', encoding='utf-8', newline='').write(rutas)

print('Generado en', os.path.abspath(DEST))
print('  imágenes  ', sum(len(v) for v in mapa.values()), 'en assets/laboratorio-notas')
print('  motor.js  ', round(len(motor.encode('utf-8')) / 1024), 'KB')
print('  catalogo.js', len(catalogo), 'perfumes ·', round(os.path.getsize(os.path.join(DEST, 'catalogo.js')) / 1024), 'KB')
print('  estilos.ts', round(len(estilos.encode('utf-8')) / 1024), 'KB ·', len(anims), 'animaciones renombradas')
