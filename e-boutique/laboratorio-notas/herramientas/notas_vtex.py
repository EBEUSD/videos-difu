"""Lectura de notas desde las descripciones de VTEX ("Notas de salida: ... Notas de corazón: ... Notas de fondo: ...")
y traducción a las notas del laboratorio. La usan diagnostico-catalogo.py y catalogo-desde-vtex.py."""
import html as H, re, unicodedata


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


# nota del laboratorio -> palabras clave (mismas que catalogo-desde-excel.py, más algunas habituales del catálogo masivo)
UI = {
    'bergamota': r'bergamota', 'limon': r'limon|\blima\b|cidra|citron|yuzu|citric', 'mandarina': r'mandarina|clementina|kumquat',
    'naranja': r'(?<!flor de )\bnaranjas?\b|bigarad|naranja amarga', 'pomelo': r'pomelo|toronja|pamplemousse',
    'anana': r'\bpina\b|anana|maracuya|fruta de la pasion|tropical|guayaba|papaya', 'lichi': r'lichi|litchi', 'mango': r'mango',
    'cerezas': r'cereza', 'frambuesa': r'frambuesa|frutos rojos|bayas rojas|frutilla|fresa', 'grosella': r'grosella|cassis|casis|\bmoras?\b|arandano',
    'manzana': r'manzana', 'pera': r'\bperas?\b', 'lavanda': r'lavand|lavandin', 'salvia': r'salvia|esclarea|cilantro|albahaca|romero|hierbas|tomillo|artemisa|estragon',
    'menta': r'\bmentas?\b|hierbabuena|peppermint',
    'te': r'\bte\b|\bmate\b|\bthe\b|\bteas?\b', 'verdes': r'galbano|notas verdes|hojas verdes|acorde verde|hojas de|hierba|cesped|bambu|pepino',
    'marinas': r'marin|sal marina|algas|oceano|acuatic|ozon|brisa', 'enebro': r'enebro|ginebra', 'durazno': r'durazno|melocoton|chabacano|damasco|albaricoque|nectarin|ciruela',
    'higo': r'\bhigos?\b|higuera', 'coco': r'\bcoco\b', 'geranio': r'geranio', 'jengibre': r'jengibre',
    'pachuli': r'pachuli|patchouli|akigalawood', 'musgo': r'musgo', 'tabaco': r'tabaco', 'almendra': r'almendra|pistacho|avellana|nuez(?! moscada)',
    'azahar': r'azahar|neroli|flor de naranj|petit ?grain', 'loto': r'loto|nenufar|magnolia|orquidea|fresia|lila|heliotropo|flor de cerezo|mimosa|camelia|narciso',
    'peonia': r'peonia', 'lirio': r'\blirios?\b(?! de florencia)|muguet|azucena',
    'violeta': r'violeta', 'iris': r'\biris\b|orris|lirio de florencia', 'tuberosa': r'tuberosa|nardo',
    'jazmin': r'jazmin|gardenia|ylang|flores blancas|frangipani|tiare|osmanthus|osmanto|madreselva',
    'rosa': r'(?<!pimienta )(?<!bayas )(?<!palo de )\brosas?\b(?! rosa)', 'azafran': r'azafran', 'canela': r'canela|clavo|especias', 'nuezMoscada': r'nuez moscada|macis',
    'cardamomo': r'cardamomo', 'pimientaNegra': r'pimienta(?! rosa)', 'pimientaRosa': r'pimienta rosa|bayas? rosas?|baies roses',
    'cedro': r'cedro|cipres|\bpino\b|amaderad|maderas?\b|guayaco|cachemir|cashmeran|palo de rosa|\bwood\b', 'abedul': r'abedul|(?<!musgo de )roble',
    'oud': r'\boud\b|agar', 'sandalo': r'sandalo', 'vetiver': r'vetiver', 'almizcle': r'almizcle|musk|almizclad',
    'ambar': r'ambar|amber|ambrox|labdan|ladano|ambergris|resina', 'benjui': r'benjui|benzoin|tolu|estoraque', 'cuero': r'cuero|gamuza|suede', 'tonka': r'tonka',
    'praline': r'pralin|caramelo|toffee|dulce de leche', 'cafe': r'\bcafe\b|espresso|cacao|chocolate',
    'incienso': r'incienso|olibano|elemi', 'mirra': r'mirra', 'vainilla': r'vainill|\bmiel\b|azucar|algodon de azucar|merengue',
}
CAPAS = {'salida': 'salida', 'corazon': 'corazón', 'fondo': 'fondo'}


def notas_de(desc):
    """{capa: [notas]} desde 'Notas de salida: ... Notas de corazón: ... Notas de fondo: ...'"""
    # los saltos de línea y párrafos se marcan con ¦: una lista de notas termina en el primero que venga después de alguna nota
    t = re.sub(r'<\s*(br|/p|/li|/div|/h\d)[^>]*>', ' ¦ ', desc or '', flags=re.I)
    t = norm(H.unescape(re.sub(r'<[^>]+>', ' ', t)))
    t = re.sub(r'\s+', ' ', t)
    out = {}
    for m in re.finditer(r'notas? (?:de |del )?(salida|corazon|fondo)\s*:?\s*(.*?)(?=notas? (?:de |del )?(?:salida|corazon|fondo)|las imagenes|$)', t):
        # la lista de notas termina en el primer punto (después suele seguir la descripción o el modo de uso)
        txt = re.split(r'\.(?:\s|$)|¦|modo de uso|aplicar|rocie', m.group(2).strip(' .;:¦'))[0].strip(' .;:¦')
        items = [x.strip(' .;:') for x in re.split(r',|;| y | e |/', txt) if x.strip(' .;:')]
        # una "nota" de más de 4 palabras es prosa, no una nota
        items = [re.sub(r'^(de |del |la |el |las |los |un |una )', '', x) for x in items if len(x.split()) <= 4]
        out.setdefault(m.group(1), items[:15])
    return out, t


def lab(nota):
    return [k for k, rx in UI.items() if re.search(rx, nota)]
