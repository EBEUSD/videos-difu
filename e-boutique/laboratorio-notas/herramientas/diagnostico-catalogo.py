"""Diagnóstico: ¿se puede armar el laboratorio con TODO el catálogo de perfumes de VTEX?
Solo lee la API pública de la tienda (no modifica nada). Para cada perfume revisa si la descripción trae
las notas por capa (salida / corazón / fondo), cuántas se pueden traducir a las notas del laboratorio
y qué notas quedan sin equivalente.

Uso (desde la carpeta laboratorio-notas):  python herramientas/diagnostico-catalogo.py
Deja el detalle en diagnostico/diagnostico-catalogo.xlsx"""
import collections, json, os, re, sys, time, urllib.request
import openpyxl
from openpyxl.styles import Font, PatternFill

aqui = os.path.dirname(os.path.abspath(__file__))
NICHO = os.path.join(aqui, '..', 'catalogo-nicho.json')
OUT = os.path.join(aqui, '..', 'diagnostico')
API = 'https://www.perfumeriasrouge.com/api/catalog_system/pub/products/search/perfumes?_from=%d&_to=%d'


sys.path.insert(0, aqui)
from notas_vtex import norm, UI, CAPAS, notas_de, lab



# perfumes que ya están en el laboratorio (catálogo de nicho)
ACTUALES = {p['id'] for p in json.load(open(NICHO, encoding='utf-8'))}

# ---------- leer el catálogo ----------
prods, desde = [], 0
while True:
    req = urllib.request.Request(API % (desde, desde + 49), headers={'User-Agent': 'laboratorio-notas-diagnostico'})
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

filas, sin_eq, uso, estados = [], collections.Counter(), collections.Counter(), collections.Counter()
lineas = collections.defaultdict(list)
for p in prods:
    spec = lambda k: ', '.join(p.get(k) or [])
    stock = any((s.get('commertialOffer') or {}).get('AvailableQuantity', 0) > 0 for it in p.get('items', []) for s in it.get('sellers', []))
    capas, texto = notas_de(p.get('description', ''))
    mapeadas = {c: sorted({k for n in capas.get(c, []) for k in lab(n)}) for c in CAPAS}
    for c in CAPAS:
        for n in capas.get(c, []):
            if not lab(n):
                sin_eq[n] += 1
    for c in CAPAS:
        for k in mapeadas[c]:
            uso[k] += 1
    total_notas = sum(len(v) for v in capas.values())
    total_lab = sum(len(v) for v in mapeadas.values())
    if len(capas) == 3 and all(mapeadas[c] for c in CAPAS):
        estado = 'Listo'
    elif capas and total_lab:
        estado = 'Parcial (falta alguna capa)'
    elif re.search(r'notas|acorde|piramide|familia olfativa', texto):
        estado = 'Notas en otro formato'
    else:
        estado = 'Sin notas en la descripción'
    estados[estado] += 1
    linea = (p.get('brand', ''), spec('Línea') or p.get('productName', ''))
    lineas[linea].append(p['productId'])
    filas.append({
        'estado': estado, 'id': p['productId'], 'marca': p.get('brand', ''), 'nombre': p.get('productName', ''),
        'línea': spec('Línea'), 'género': spec('Género'), 'aroma': spec('Aroma'), 'clasificación': spec('Clasificación'),
        'con stock': 'sí' if stock else 'no', 'ya en el lab': 'sí' if p['productId'] in ACTUALES else '',
        'salida': ', '.join(capas.get('salida', [])), 'corazón': ', '.join(capas.get('corazon', [])), 'fondo': ', '.join(capas.get('fondo', [])),
        'notas lab': ' · '.join('%s: %s' % (CAPAS[c], ', '.join(mapeadas[c]) or '—') for c in CAPAS),
        'notas leídas': total_notas, 'traducidas': sum(1 for c in CAPAS for n in capas.get(c, []) if lab(n)),
        'url': 'https://www.perfumeriasrouge.com/%s/p' % p.get('linkText', ''),
    })

# ---------- resumen ----------
n = len(filas)
con_stock = [f for f in filas if f['con stock'] == 'sí']
listos_stock = [f for f in con_stock if f['estado'] == 'Listo']
leidas = sum(f['notas leídas'] for f in filas)
trad = sum(f['traducidas'] for f in filas)
generos = collections.Counter(f['género'] or '(vacío)' for f in filas)
aromas = collections.Counter(a.strip() for f in filas for a in f['aroma'].split(',') if a.strip())
multi = {k: v for k, v in lineas.items() if len(v) > 1}

R = [
    ('Perfumes en la categoría', n),
    ('Con stock hoy', len(con_stock)),
    ('Ya están en el laboratorio (nicho)', sum(1 for f in filas if f['ya en el lab'])),
    ('', ''),
] + [('Estado: ' + e, '%d (%d%%)' % (c, round(100 * c / n))) for e, c in estados.most_common()] + [
    ('', ''),
    ('Listos y con stock', len(listos_stock)),
    ('Notas leídas en total', leidas),
    ('Notas traducidas a las del laboratorio', '%d (%d%%)' % (trad, round(100 * trad / max(1, leidas)))),
    ('Notas distintas sin equivalente', len(sin_eq)),
    ('Notas del laboratorio que nunca aparecen', ', '.join(k for k in UI if not uso[k]) or 'ninguna'),
    ('', ''),
    ('Líneas con más de una versión (EDT/EDP/sets…)', '%d líneas · %d productos' % (len(multi), sum(len(v) for v in multi.values()))),
    ('Perfumes únicos si se agrupa por línea', len(lineas)),
    ('', ''),
    ('Género', ' · '.join('%s %d' % kv for kv in generos.most_common())),
    ('Aroma (campo de VTEX)', ' · '.join('%s %d' % kv for kv in aromas.most_common(15))),
]
print()
for k, v in R:
    print(('%-48s %s' % (k, v)) if k else '')
print('\nNotas sin equivalente más frecuentes:')
for k, v in sin_eq.most_common(25):
    print('  %4d  %s' % (v, k))

# ---------- Excel ----------
os.makedirs(OUT, exist_ok=True)
wb = openpyxl.Workbook()
neg = Font(bold=True)
ws = wb.active; ws.title = 'Resumen'
for k, v in R:
    ws.append([k, v])
ws.column_dimensions['A'].width = 48; ws.column_dimensions['B'].width = 110
for c in ws['A']: c.font = neg

ws = wb.create_sheet('Perfumes')
cols = list(filas[0])
ws.append(cols)
color = {'Listo': 'E2F0D9', 'Parcial (falta alguna capa)': 'FFF2CC', 'Notas en otro formato': 'FCE4D6', 'Sin notas en la descripción': 'F8CBAD'}
orden = {'Sin notas en la descripción': 0, 'Notas en otro formato': 1, 'Parcial (falta alguna capa)': 2, 'Listo': 3}
for f in sorted(filas, key=lambda f: (orden[f['estado']], f['con stock'] != 'sí', f['marca'], f['nombre'])):
    ws.append([f[c] for c in cols])
    ws.cell(ws.max_row, 1).fill = PatternFill('solid', fgColor=color[f['estado']])
for c in ws[1]: c.font = neg
ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
for col, w in zip('ABCDEFGHIJKLMNOPQ', (26, 8, 18, 34, 22, 10, 22, 10, 9, 10, 40, 40, 40, 60, 8, 8, 50)):
    ws.column_dimensions[col].width = w

ws = wb.create_sheet('Notas sin equivalente')
ws.append(['nota', 'perfumes'])
for k, v in sin_eq.most_common():
    ws.append([k, v])
for c in ws[1]: c.font = neg
ws.column_dimensions['A'].width = 40

ws = wb.create_sheet('Uso de notas del lab')
ws.append(['nota del laboratorio', 'perfumes'])
for k in UI:
    ws.append([k, uso[k]])
for c in ws[1]: c.font = neg

dest = os.path.join(OUT, 'diagnostico-catalogo.xlsx')
wb.save(dest)
print('\nDetalle en', os.path.abspath(dest))
