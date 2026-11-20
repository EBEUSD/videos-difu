r"""Lleva el catálogo del laboratorio al tema de VTEX IO (bloque `laboratorio-notas` de Rouge-VTEX-theme).

El código del laboratorio (motor.js y estilos.ts) se edita directamente en el tema; este programa no lo toca.
Escribe solamente:
  react/components/laboratorio-notas/catalogo.js el catálogo (copia de catalogo.json; la tienda usa primero el de
                                                 GitHub Pages y este queda de respaldo)
  react/components/laboratorio-notas/marcas.ts   las marcas del catálogo (desplegable del Site Editor)
  assets/laboratorio-notas/                      las imágenes de notas y frasco que usa el motor.js del tema
  store/blocks/laboratorio-notas.jsonc y la ruta  solo si todavía no existen en el tema

Uso (desde la carpeta laboratorio-notas):
  python herramientas/armar-vtex.py                       (busca el tema en ../../../Rouge-VTEX-theme)
  python herramientas/armar-vtex.py C:\ruta\al\tema"""
import json, os, re, shutil, sys

sys.stdout.reconfigure(encoding='utf-8')
aqui = os.path.dirname(os.path.abspath(__file__))
TEMA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(aqui, '..', '..', '..', '..', 'Rouge-VTEX-theme')
DEST = os.path.join(TEMA, 'react', 'components', 'laboratorio-notas')
if not os.path.isfile(os.path.join(TEMA, 'manifest.json')):
    raise SystemExit('No encuentro el tema en ' + os.path.abspath(TEMA))


def escribir(ruta, texto):
    """solo si cambió: con "vtex link" corriendo, reenviar el catálogo (600 KB) sin cambios hace que VTEX lo rechace (413)"""
    if os.path.isfile(ruta) and open(ruta, encoding='utf-8', newline='').read() == texto:
        return
    open(ruta, 'w', encoding='utf-8', newline='\n').write(texto)


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



# ---------- Imágenes en assets/ del tema + bloque con el mapa de imágenes ----------
# El builder "store" convierte cada "assets/..." de las props en la URL publicada (también dentro de objetos).
MOTOR_TEMA = os.path.join(DEST, 'motor.js')
if not os.path.isfile(MOTOR_TEMA):
    raise SystemExit('El tema no tiene motor.js en ' + os.path.abspath(DEST))
referencia = open(MOTOR_TEMA, encoding='utf-8').read()
IMGS = os.path.join(aqui, '..', 'imagenes')
mapa = {}
for tipo in ('notas', 'frasco'):
    destino = os.path.join(TEMA, 'assets', 'laboratorio-notas', tipo)
    os.makedirs(destino, exist_ok=True)
    mapa[tipo] = {}
    for f in sorted(os.listdir(os.path.join(IMGS, tipo))):
        # solo las que usa el laboratorio (en la carpeta puede haber otras, como banners)
        if f.lower().endswith('.webp') and "'%s'" % f in referencia:
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
          'toggle-layout#laboratorio-notas-capas', 'toggle-layout#laboratorio-notas-carrusel']
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
    'toggle-layout#laboratorio-notas-carrusel': {
        'title': '[6] [On/Off] Carrusel de productos',
        'children': ['flex-layout.row#laboratorio-notas-carrusel'],
        'props': {'renderChildren': True},
    },
    'flex-layout.row#laboratorio-notas-carrusel': {
        'children': ['rich-text#laboratorio-notas-carrusel-titulo', 'list-context.product-list#laboratorio-notas-carrusel'],
        'props': {'width': '100%', 'blockClass': ['prods-landing']},
    },
    'rich-text#laboratorio-notas-carrusel-titulo': {
        'title': 'Título del carrusel',
        'props': {'text': 'Perfumes para descubrir', 'blockClass': 'titulo-home', 'font': 't-heading-4'},
    },
    'list-context.product-list#laboratorio-notas-carrusel': {
        'title': 'Productos del carrusel',
        'blocks': ['product-summary.shelf#rougeHotSaleNew'],
        'children': ['slider-layout#carrusel-landing-22'],
    },
}
jsonc = (json.dumps(bloque, ensure_ascii=False, indent=2) + '\n')
BLOQUE = os.path.join(TEMA, 'store', 'blocks', 'laboratorio-notas.jsonc')
if not os.path.isfile(BLOQUE):
    escribir(BLOQUE, jsonc)
else:
    actual = open(BLOQUE, encoding='utf-8').read()
    faltan = [r for t in mapa.values() for r in t.values() if r not in actual]
    if faltan:
        print('⚠ laboratorio-notas.jsonc del tema no tiene estas imágenes en "archivos" (agregalas a mano):')
        for r in faltan:
            print('   ', r)
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
print('  catalogo.js', len(catalogo), 'perfumes ·', round(os.path.getsize(os.path.join(DEST, 'catalogo.js')) / 1024), 'KB')
