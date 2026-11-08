"""Arma catalogo.json (el catálogo del laboratorio) con:
  1. los perfumes de nicho curados a mano (catalogo-nicho.json, sale de catalogo-desde-excel.py), tal cual;
  2. todos los perfumes de la categoría Perfumes de VTEX que estén "listos": descripción con notas de salida,
     corazón y fondo, y en cada capa al menos una nota que el laboratorio reconoce (ver diagnostico-catalogo.py).

Solo perfumes individuales (sin kits, sets, regalos por compra ni desodorantes) y con stock hoy.
Género, familias y momento salen de las especificaciones de VTEX (Género, Aroma, Clasificación).
Las versiones del mismo perfume (EDT / EDP / tamaños) comparten el campo "l": el laboratorio recomienda una sola.

Uso (desde la carpeta laboratorio-notas):
  python herramientas/catalogo-desde-vtex.py
  python herramientas/catalogo-desde-vtex.py --cache archivo.json   (usa un catálogo ya bajado, para probar)
Después: armar-sandbox.py / armar-vtex.py como siempre."""
import collections, json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notas_vtex import norm, CAPAS, notas_de, lab

aqui = os.path.dirname(os.path.abspath(__file__))
NICHO = os.path.join(aqui, '..', 'catalogo-nicho.json')
OUT = os.path.join(aqui, '..', 'catalogo.json')
API = 'https://www.perfumeriasrouge.com/api/catalog_system/pub/products/search/perfumes?_from=%d&_to=%d'
CAPA = {'salida': 't', 'corazon': 'h', 'fondo': 'b'}

# Aroma de VTEX -> familia del laboratorio (las que usan el perfil y el "por qué")
FAMILIA = {
    'Floral': 'Floral', 'Rosas': 'Floral', 'Amaderada': 'Amaderada', 'Almizcle': 'Almizclada', 'Musk': 'Almizclada',
    'Vainilla': 'Gourmand', 'Dulce': 'Gourmand', 'Gourmand': 'Gourmand', 'Coco': 'Gourmand', 'Frutal': 'Frutal',
    'Oriental': 'Ambarada', 'Ámbar': 'Ambarada', 'Aromática': 'Aromática', 'Fougère': 'Aromática', 'Cítrica': 'Cítrica',
    'Especiada': 'Especiada', 'Cuero': 'Cuero', 'Chipre': 'Chipre', 'Acuática': 'Acuática', 'Marina': 'Acuática', 'Verde': 'Verde',
}
# si VTEX no tiene Aroma: familia según las notas del laboratorio
FAM_NOTA = {
    'Cítrica': 'bergamota limon mandarina naranja pomelo', 'Frutal': 'anana lichi mango cerezas frambuesa grosella manzana pera durazno higo',
    'Aromática': 'lavanda salvia enebro geranio', 'Verde': 'verdes te', 'Acuática': 'marinas',
    'Floral': 'azahar loto violeta iris jazmin rosa', 'Especiada': 'azafran canela cardamomo pimientaNegra pimientaRosa jengibre',
    'Amaderada': 'cedro abedul oud sandalo vetiver pachuli musgo', 'Almizclada': 'almizcle', 'Ambarada': 'ambar incienso mirra',
    'Cuero': 'cuero tabaco', 'Gourmand': 'tonka vainilla almendra coco',
}
DIA, NOCHE = {'Cítrica', 'Acuática', 'Verde', 'Aromática'}, {'Ambarada', 'Cuero', 'Especiada', 'Gourmand'}


def spec(p, k):
    return p.get(k) or []


def leer_catalogo():
    if '--cache' in sys.argv:
        return json.load(open(sys.argv[sys.argv.index('--cache') + 1], encoding='utf-8'))
    prods, desde = [], 0
    while True:
        req = urllib.request.Request(API % (desde, desde + 49), headers={'User-Agent': 'laboratorio-notas'})
        for intento in range(3):
            try:
                lote = json.load(urllib.request.urlopen(req, timeout=30)); break
            except Exception:
                if intento == 2: raise
                time.sleep(3)
        prods += lote
        desde += 50
        print('\rleídos', len(prods), end='', flush=True)
        if len(lote) < 50 or desde >= 2500:
            break
        time.sleep(0.2)
    print()
    return prods


CONC = r'\b(eau de (parfum|toilette|cologne)|extrait de parfum|edp|edt|edc|edpi)\b|\b\d+ ?ml\b'


def nombre_limpio(nombre):
    n = re.sub(CONC, ' ', nombre, flags=re.I)
    return re.sub(r'\s+', ' ', n).strip(' -')


def clave_linea(marca, nombre):
    # la recarga y el frasco recargable son el mismo perfume
    n = re.sub(r'\b(refill|recargable|recarga|repuesto)\b', ' ', nombre, flags=re.I)
    return norm(marca + '|' + nombre_limpio(n)).replace(' ', '')


def con_acentos(nota, original):
    """las notas se leen sin acentos; se recuperan de las palabras de la descripción original"""
    dic = {norm(w): w for w in re.findall(r'[^\W\d_]+', original.lower())}
    txt = ' '.join(dic.get(w, w) for w in nota.split())
    return txt[:1].upper() + txt[1:]


def imagen(p, item):
    url = (item.get('images') or [{}])[0].get('imageUrl', '')
    return re.sub(r'(/arquivos/ids/\d+)(?:-\d+-\d+)?/', r'\g<1>-400-400/', url.split('?')[0])


def mejor_sku(p):
    best = None
    for it in p.get('items', []):
        for s in it.get('sellers', []):
            c = s.get('commertialOffer') or {}
            if c.get('AvailableQuantity', 0) > 0 and c.get('Price', 0) > 0 and (not best or c['Price'] < best[0]):
                best = (c['Price'], it, s['sellerId'])
    return best


def excluido(p):
    nombre = norm(p.get('productName', ''))
    return ((spec(p, 'Tipo') and 'Perfumes' not in spec(p, 'Tipo'))
            or (spec(p, 'Formato') and 'Individual' not in spec(p, 'Formato'))
            or any(x.startswith('Kit') or x in ('Desodorante', 'Body Splash', 'Bruma Capilar', 'Cepillo', 'Gel de Ducha') for x in spec(p, 'Producto'))
            or re.search(r'\bset\b|\bkit\b|\+|vincha|neceser|regalo|body splash|desodorante', nombre))


nicho = json.load(open(NICHO, encoding='utf-8'))
ids_nicho = {p['id'] for p in nicho}
motivos, P = collections.Counter(), []
for p in leer_catalogo():
    pid = p['productId']
    if pid in ids_nicho:
        motivos['ya está en el nicho curado'] += 1; continue
    if excluido(p):
        motivos['kit, set, regalo o no es perfume'] += 1; continue
    capas, _ = notas_de(p.get('description', ''))
    claves = {c: [] for c in CAPAS}
    for c in CAPAS:
        for n in capas.get(c, []):
            for k in lab(n):
                if k not in claves[c]:
                    claves[c].append(k)
    if not (len(capas) == 3 and all(claves[c] for c in CAPAS)):
        motivos['notas incompletas en la descripción'] += 1; continue
    best = mejor_sku(p)
    if not best:
        motivos['sin stock'] += 1; continue
    _, item, seller = best

    genero = (spec(p, 'Género') or [''])[0]
    if genero not in ('Mujer', 'Hombre', 'Unisex'):
        prod = ' '.join(spec(p, 'Producto'))
        genero = 'Mujer' if 'Mujer' in prod else 'Hombre' if 'Hombre' in prod else 'Unisex'
    fams = []
    for a in spec(p, 'Aroma'):
        f = FAMILIA.get(a)
        if f and f not in fams:
            fams.append(f)
    if not fams:
        todas = [k for c in CAPAS for k in claves[c]]
        cuenta = collections.Counter(f for k in todas for f, ks in FAM_NOTA.items() if k in ks.split())
        fams = [f for f, _ in cuenta.most_common(2)]
    clas = ' '.join(spec(p, 'Clasificación'))
    dia = len(DIA & set(fams)) + (1 if re.search(r'EDC|EDT', clas) else 0)
    noche = len(NOCHE & set(fams)) + (1 if re.search(r'Parfum|Elixir|Intense', clas) else 0)
    momento = 'Día' if dia > noche else 'Noche' if noche > dia else 'Ambos'

    desc = re.sub(r'<[^>]+>', ' ', p.get('description', ''))
    d = [[[con_acentos(n, desc), lab(n)] for n in capas[c]] for c in CAPAS]
    P.append({'id': pid, 'name': nombre_limpio(p['productName']), 'house': p.get('brand', ''),
              'url': 'https://www.perfumeriasrouge.com/%s/p' % p['linkText'], 'img': imagen(p, item),
              'g': genero, 'f': fams[:3], 'm': momento,
              't': claves['salida'], 'h': claves['corazon'], 'b': claves['fondo'], 'd': d,
              'sku': item['itemId'], 'sel': seller})
    motivos['agregado'] += 1

# versiones del mismo perfume: misma marca y mismo nombre sin concentración ni tamaño
todos = nicho + P
lineas = collections.Counter(clave_linea(p['house'], p['name']) for p in todos)
for p in todos:
    p.pop('l', None)
    p.pop('rf', None)
    k = clave_linea(p['house'], p['name'])
    if lineas[k] > 1:
        p['l'] = k
        # recarga: a igual coincidencia se muestra el perfume original
        if re.search(r'\b(refill|recargable|recarga|repuesto)\b', p['name'], re.I):
            p['rf'] = 1

json.dump(todos, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('catalogo.json:', len(todos), 'perfumes (%d de nicho + %d del catálogo de VTEX)' % (len(nicho), len(P)))
print('  ', ' · '.join('%s %d' % kv for kv in motivos.most_common()))
print('   versiones agrupadas:', sum(1 for v in lineas.values() if v > 1), 'perfumes con más de una versión ·',
      len(lineas), 'perfumes distintos')
print('   género:', dict(collections.Counter(p['g'] for p in P)), '· momento:', dict(collections.Counter(p['m'] for p in P)))
print('  ', round(os.path.getsize(OUT) / 1024), 'KB')
