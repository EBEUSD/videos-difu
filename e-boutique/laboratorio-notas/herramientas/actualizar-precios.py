"""Genera precios.json con precio, precio de lista, stock y SKU de cada perfume del laboratorio.
Lo corre GitHub solo cada 2 horas (.github/workflows/precios-laboratorio.yml) y el laboratorio lo lee desde
GitHub Pages, porque dentro del Sandbox de VTEX no puede consultar la API de la tienda.
Uso manual:  python herramientas/actualizar-precios.py        (desde la carpeta laboratorio-notas)"""
import datetime, json, os, re, sys, time, urllib.request

aqui = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(aqui, '..', 'arma-perfume-notas.html')
OUT = os.path.join(aqui, '..', 'precios.json')
API = 'https://www.perfumeriasrouge.com/api/catalog_system/pub/products/search?fq=productId:'

html = open(HTML, encoding='utf-8').read()
bloque = html[html.index('var P = ['):]
bloque = bloque[:bloque.index('];')]
ids = re.findall(r'^\s*\{"id":"(\d+)"', bloque, re.M)
if not ids:
    raise SystemExit('No encontré productos en el catálogo')


def consultar(pid):
    req = urllib.request.Request(API + pid, headers={'User-Agent': 'laboratorio-notas-precios'})
    for intento in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=25))
        except Exception:
            if intento == 2:
                raise
            time.sleep(2)


# misma lógica que el laboratorio en vivo: la presentación más barata con stock
precios, errores = {}, 0
for pid in ids:
    try:
        d = consultar(pid)
    except Exception as e:
        errores += 1
        print('error', pid, e, file=sys.stderr)
        continue
    best, n = None, 0
    for it in (d[0].get('items', []) if d else []):
        for s in it.get('sellers', []):
            c = s.get('commertialOffer', {})
            if c.get('AvailableQuantity', 0) > 0 and c.get('Price', 0) > 0:
                n += 1
                if not best or c['Price'] < best['price']:
                    best = {'price': c['Price'], 'list': c.get('ListPrice', 0), 'sku': it['itemId'],
                            'seller': s['sellerId'], 'size': it.get('name', '')}
    if best:
        best['many'] = n > 1
        precios[pid] = best
    else:
        precios[pid] = {'out': True}
    time.sleep(0.05)

# si fallaron demasiadas consultas, no pisar el archivo bueno anterior
if errores > len(ids) * 0.2:
    raise SystemExit(f'Demasiados errores ({errores}/{len(ids)}): no se actualiza precios.json')

ahora = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump({'actualizado': ahora, 'p': precios}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'), sort_keys=True)
con = sum(1 for v in precios.values() if 'price' in v)
print(f'precios.json: {con} con stock · {len(precios) - con} sin stock · {errores} errores')
