"""Uso: python herramientas/catalogo-desde-excel.py Productos_fragancias_nicho_Rouge.xlsx catalogo-nicho.json
(después correr herramientas/catalogo-desde-vtex.py, que suma el resto del catálogo y los SKU)
Convierte Productos_fragancias_nicho_Rouge.xlsx en catalogo-nicho.json (los perfumes de nicho curados).
Cada nota del Excel se mapea a una (o más) de las 37 notas con imagen del laboratorio;
la capa sale del texto de la pirámide (salida / corazón / fondo) o, si no está, de la familia de la nota."""
import sys, re, json, unicodedata, collections
import openpyxl

XLSX, SALIDA = sys.argv[1], sys.argv[2]


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


# nota del laboratorio: (capa por defecto, notas del Excel que representa, palabras clave en la pirámide, es la principal para esas notas)
UI = {
    'bergamota':     ('t', ['Bergamota'], r'bergamota', 1),
    'limon':         ('t', ['Limón', 'Lima'], r'limon|\blima\b|cidra|citron|yuzu', 1),
    'mandarina':     ('t', ['Mandarina'], r'mandarina|clementina|kumquat', 1),
    'naranja':       ('t', ['Naranja'], r'(?<!flor de )\bnaranjas?\b|bigarad', 1),
    'pomelo':        ('t', ['Pomelo'], r'pomelo|toronja|pamplemousse', 1),
    'anana':         ('t', ['Frutas tropicales'], r'pina|anana|maracuya|fruta de la pasion|tropical', 1),
    'lichi':         ('t', ['Frutas tropicales'], r'lichi|litchi', 0),
    'mango':         ('t', ['Frutas tropicales'], r'mango', 0),
    'cerezas':       ('t', ['Frutos rojos'], r'cereza', 0),
    'frambuesa':     ('t', ['Frutos rojos'], r'frambuesa|frutos rojos|bayas rojas|frutilla|fresa', 1),
    'grosella':      ('t', ['Frutos rojos'], r'grosella|cassis|casis|\bmoras?\b|arandano', 0),
    'manzana':       ('t', ['Manzana'], r'manzana', 1),
    'pera':          ('t', ['Pera'], r'\bperas?\b', 1),
    'lavanda':       ('t', ['Lavanda'], r'lavand', 1),
    'salvia':        ('t', ['Salvia', 'Albahaca', 'Romero'], r'salvia|albahaca|romero|hierbas', 1),
    'menta':         ('t', ['Menta'], r'\bmentas?\b|hierbabuena', 1),
    'te':            ('t', ['Té'], r'\bte\b|\bmate\b', 1),
    'verdes':        ('t', ['Notas verdes'], r'galbano|notas verdes|hojas verdes|acorde verde', 1),
    'marinas':       ('t', ['Notas marinas'], r'marin|sal marina|algas|oceano|acuatic', 1),
    'enebro':        ('t', ['Enebro'], r'enebro', 1),
    'durazno':       ('t', ['Durazno'], r'durazno|melocoton|damasco|albaricoque', 1),
    'higo':          ('t', ['Higo'], r'\bhigos?\b|higuera', 1),
    'coco':          ('h', ['Coco'], r'\bcoco\b', 1),
    'geranio':       ('h', ['Geranio'], r'geranio', 1),
    'jengibre':      ('t', ['Jengibre'], r'jengibre', 1),
    'pachuli':       ('b', ['Pachulí'], r'pachuli|patchouli', 1),
    'musgo':         ('b', ['Musgo'], r'musgo', 1),
    'tabaco':        ('b', ['Tabaco'], r'tabaco', 1),
    'almendra':      ('b', ['Almendra'], r'almendra', 1),
    'azahar':        ('h', ['Neroli'], r'azahar|neroli|flor de naranj|petit ?grain', 1),
    'loto':          ('h', ['Magnolia', 'Orquídea', 'Fresia'], r'loto|nenufar|magnolia|orquidea|fresia', 1),
    'peonia':        ('h', ['Peonía'], r'peonia', 1),
    'lirio':         ('h', ['Lirio'], r'\blirios?\b(?! de florencia)|muguet|azucena', 1),
    'violeta':       ('h', ['Violeta'], r'violeta', 1),
    'iris':          ('h', ['Iris'], r'\biris\b|orris', 1),
    'jazmin':        ('h', ['Jazmín', 'Flores blancas', 'Gardenia', 'Ylang-ylang'], r'jazmin|gardenia|ylang|flores blancas', 1),
    'tuberosa':      ('h', ['Nardo'], r'tuberosa|nardo', 1),
    'rosa':          ('h', ['Rosa'], r'(?<!pimienta )(?<!bayas )(?<!baies )\brosas?\b(?! rosa)', 1),
    'azafran':       ('h', ['Azafrán'], r'azafran', 1),
    'canela':        ('h', ['Canela', 'Clavo'], r'canela|clavo', 1),
    'nuezMoscada':   ('h', ['Nuez moscada'], r'nuez moscada|macis', 1),
    'cardamomo':     ('h', ['Cardamomo'], r'cardamomo', 1),
    'pimientaNegra': ('h', ['Pimienta'], r'pimienta(?! rosa)', 1),
    'pimientaRosa':  ('h', ['Pimienta'], r'pimienta rosa|bayas? rosas?|baies roses', 0),
    'cedro':         ('b', ['Cedro', 'Ciprés', 'Notas amaderadas'], r'cedro|cipres|\bpino\b|amaderad|maderas?\b', 1),
    'abedul':        ('b', ['Roble'], r'abedul|(?<!musgo de )roble', 1),
    'oud':           ('b', ['Oud'], r'\boud\b|agar', 1),
    'sandalo':       ('b', ['Sándalo'], r'sandalo', 1),
    'vetiver':       ('b', ['Vetiver'], r'vetiver', 1),
    'almizcle':      ('b', ['Almizcle'], r'almizcle|musk', 1),
    'ambar':         ('b', ['Ámbar'], r'ambar|ambrox|labdan', 1),
    'benjui':        ('b', ['Benjuí'], r'benjui|tolu', 1),
    'cuero':         ('b', ['Cuero', 'Gamuza'], r'cuero|gamuza|suede', 1),
    'tonka':         ('b', ['Haba tonka'], r'tonka', 1),
    'praline':       ('b', ['Praliné', 'Caramelo'], r'pralin|caramelo|toffee', 1),
    'cafe':          ('b', ['Café', 'Cacao'], r'\bcafe\b|cacao|chocolate', 1),
    'incienso':      ('b', ['Incienso'], r'incienso|olibano', 1),
    'mirra':         ('b', ['Mirra'], r'mirra', 1),
    'vainilla':      ('b', ['Vainilla', 'Miel'], r'vainill|\bmiel\b', 1),
}
# notas del Excel sin imagen equivalente: se muestran pero no suman
EXTRA = {'Licor': ('h', r'whisky|licor|\bron\b|cognac|ginebra')}

# Notas que se buscan también en el TEXTO de la pirámide (la columna "notas" del Excel resume y deja afuera varias).
# Solo términos concretos; las genéricas ("notas amaderadas") no se buscan en el texto para evitar falsos positivos.
TEXT = {
    'Bergamota': r'bergamota', 'Limón': r'limon|citron|cidra|yuzu', 'Lima': r'\blimas?\b', 'Mandarina': r'mandarina|clementina',
    'Naranja': r'\bnaranjas?\b', 'Pomelo': r'pomelo|toronja', 'Neroli': r'neroli|azahar|flor de naranj|petit ?grain',
    'Rosa': r'(?<!pimienta )(?<!palo de )(?<!bayas )\brosas?\b(?! rosa)', 'Jazmín': r'jazmin', 'Iris': r'\biris\b|orris',
    'Violeta': r'violeta', 'Nardo': r'nardo|tuberosa', 'Peonía': r'peonia', 'Magnolia': r'magnolia', 'Lirio': r'\blirios?\b(?! de florencia)|muguet|azucena', 'Fresia': r'fresia',
    'Gardenia': r'gardenia', 'Ylang-ylang': r'ylang', 'Orquídea': r'orquidea', 'Flores blancas': r'flores blancas',
    'Lavanda': r'lavand', 'Salvia': r'salvia', 'Albahaca': r'albahaca', 'Menta': r'\bmenta\b|hierbabuena', 'Romero': r'romero',
    'Geranio': r'geranio', 'Té': r'\bte (negro|verde|rojo|blanco|matcha|earl|oolong|ahumado)|\bmate\b',
    'Pera': r'\bperas?\b', 'Manzana': r'manzana', 'Durazno': r'durazno|melocoton', 'Coco': r'\bcoco\b', 'Higo': r'\bhigos?\b',
    'Frutos rojos': r'frutos rojos|bayas rojas|frambuesa|fresa|frutilla|grosella|cassis|casis|\bmoras?\b|arandano|cereza',
    'Frutas tropicales': r'\bpina\b|anana|mango|lichi|litchi|maracuya|fruta de la pasion|tropical',
    'Pimienta': r'pimienta', 'Cardamomo': r'cardamomo', 'Jengibre': r'jengibre', 'Canela': r'canela', 'Clavo': r'\bclavo',
    'Azafrán': r'azafran', 'Nuez moscada': r'nuez moscada', 'Cedro': r'cedro', 'Sándalo': r'sandalo', 'Vetiver': r'vetiver',
    'Pachulí': r'pachuli|patchouli', 'Oud': r'\boud\b|madera de agar', 'Roble': r'(?<!musgo de )roble', 'Musgo': r'musgo', 'Ciprés': r'cipres',
    'Enebro': r'enebro', 'Ámbar': r'\bambar|ambrox|ambergris', 'Vainilla': r'vainill', 'Haba tonka': r'tonka', 'Benjuí': r'benjui',
    'Incienso': r'incienso|olibano', 'Mirra': r'mirra', 'Almizcle': r'almizcle|\bmusk', 'Cuero': r'cuero', 'Gamuza': r'gamuza|suede',
    'Tabaco': r'tabaco', 'Miel': r'\bmiel\b', 'Praliné': r'pralin', 'Caramelo': r'caramelo|toffee', 'Cacao': r'cacao|chocolate', 'Café': r'\bcafe\b',
    'Almendra': r'almendra', 'Licor': r'whisky|licor|\bron\b|cognac|ginebra', 'Notas marinas': r'notas marinas|acorde marino|sal marina|algas',
    'Notas verdes': r'notas verdes|galbano|hojas verdes|acorde verde',
}

TAG2UI = collections.defaultdict(list)
for k, (lay, tags, kw, prim) in UI.items():
    for t in tags:
        TAG2UI[t].append(k)


def segments(text):
    """{'t': '...', 'h': '...', 'b': '...'} a partir de 'Notas de salida: ... / Notas de corazón: ... / Notas de fondo: ...'"""
    n = norm(text)
    out = {}
    for m in re.finditer(r'notas? de (salida|corazon|fondo)\s*:(.*?)(?=notas? [a-z ]{0,20}:|$)', n):
        out[{'salida': 't', 'corazon': 'h', 'fondo': 'b'}[m.group(1)]] = m.group(2)
    return out, n


wb = openpyxl.load_workbook(XLSX)
rows = [r for r in wb['Productos'].iter_rows(min_row=2, values_only=True) if r[0]]
P, stats, ADDED = [], collections.Counter(), []
for r in rows:
    pid, house, name, url, img, gen = (str(x).strip() if x else '' for x in r[:6])
    img = re.sub(r'(/arquivos/ids/\d+)(?:-\d+-\d+)?/', r'\g<1>-400-400/', img)  # versión reducida de VTEX (~6 KB)
    tags = [t.strip() for t in (r[8] or '').split(';') if t.strip()]
    seg, full = segments(r[9])
    # notas que figuran en la pirámide pero no en la columna: se suman con la capa donde aparecen
    forced = {}
    for tag, rx in TEXT.items():
        if tag in tags:
            continue
        lay = next((l for l in 'thb' if l in seg and re.search(rx, seg[l])), None)
        if lay:
            forced[tag] = lay
            tags.append(tag)
    stats['notas sumadas del texto'] += len(forced)
    ADDED.append((house, name, r[8], r[9], dict(forced)))
    lay_keys = {'t': [], 'h': [], 'b': []}
    lay_tags = {'t': [], 'h': [], 'b': []}
    for tag in tags:
        cands = TAG2UI.get(tag, [])
        if cands:
            keys = [k for k in cands if re.search(UI[k][2], full)] or [k for k in cands if UI[k][3]] or cands[:1]
            kw = '|'.join(UI[k][2] for k in keys)
            deflay = UI[keys[0]][0]
        elif tag in EXTRA:
            keys, (deflay, kw) = [], EXTRA[tag]
        else:
            stats['sin mapa: ' + tag] += 1
            keys, deflay, kw = [], 'h', re.escape(norm(tag))
        lay = forced.get(tag) or next((l for l in 'thb' if l in seg and re.search(kw, seg[l])), deflay)
        stats['capa ' + ('pirámide' if lay in seg and re.search(kw, seg.get(lay, '')) else 'por defecto')] += 1
        for k in keys:
            if k not in lay_keys[lay]:
                lay_keys[lay].append(k)
        lay_tags[lay].append([tag, keys])
    P.append({'id': pid, 'name': name, 'house': house, 'url': url, 'img': img, 'g': gen,
              'f': [x for x in (r[6], r[7]) if x], 'm': r[10] or '',
              't': lay_keys['t'], 'h': lay_keys['h'], 'b': lay_keys['b'],
              'd': [lay_tags['t'], lay_tags['h'], lay_tags['b']]})

# uso de cada nota del laboratorio (para detectar notas que nunca coinciden)
use = collections.Counter(k for p in P for l in 'thb' for k in p[l])
print(len(P), 'productos')
print(dict(stats))
print('notas sin productos:', [k for k in UI if not use[k]])
print('uso:', use.most_common())

DRY = '--dry' in sys.argv
if DRY:
    import random
    con = [a for a in ADDED if a[4]]
    print('productos con notas sumadas:', len(con), 'de', len(ADDED), '| promedio por producto:', round(sum(len(a[4]) for a in ADDED) / len(ADDED), 2))
    print('más sumadas:', collections.Counter(t for a in ADDED for t in a[4]).most_common(15))
    random.seed(7)
    for a in [x for x in con if x[1] == 'Valero'] + random.sample(con, 7):
        print('\n##', a[0], '-', a[1]); print('  columna:', a[2]); print('  pirámide:', a[3]); print('  SUMA:', a[4])
    sys.exit()

json.dump(P, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('ok')
