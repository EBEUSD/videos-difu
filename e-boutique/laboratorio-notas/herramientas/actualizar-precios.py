"""Genera precios.json con precio, precio de lista, stock y SKU de cada perfume del laboratorio.
Lo corre GitHub solo cada 2 horas (.github/workflows/precios-laboratorio.yml) y el laboratorio lo lee desde
GitHub Pages, porque dentro del Sandbox de VTEX no puede consultar la API de la tienda.
Uso manual:  python herramientas/actualizar-precios.py        (desde la carpeta laboratorio-notas)"""
import datetime, json, os, re, sys, time, urllib.request

aqui = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(aqui, '..', 'catalogo.json')
OUT = os.path.join(aqui, '..', 'precios.json')
API = 'https://www.perfumeriasrouge.com/api/catalog_system/pub/products/search?'

ids = [p['id'] for p in json.load(open(CATALOGO, encoding='utf-8'))]
if not ids:
    raise SystemExit('No encontré productos en el catálogo')


def consultar(lote):
    """hasta 50 productos por consulta (repetir fq=productId:... los suma)"""
    q = '&'.join('fq=productId:' + pid for pid in lote) + '&_from=0&_to=49'
    req = urllib.request.Request(API + q, headers={'User-Agent': 'laboratorio-notas-precios'})
    for intento in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception:
            if intento == 2:
                raise
            time.sleep(2)


# misma lógica que el laboratorio en vivo: la presentación más barata con stock
precios, errores = {}, 0
for i in range(0, len(ids), 50):
    lote = ids[i:i + 50]
    try:
        datos = {p['productId']: p for p in consultar(lote)}
    except Exception as e:
        errores += len(lote)
        print('error', lote[0], '…', e, file=sys.stderr)
        continue
    for pid in lote:
        best, n = None, 0
        for it in (datos[pid].get('items', []) if pid in datos else []):
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
    time.sleep(0.2)

# si fallaron demasiadas consultas, no pisar el archivo bueno anterior
if errores > len(ids) * 0.2:
    raise SystemExit(f'Demasiados errores ({errores}/{len(ids)}): no se actualiza precios.json')

ahora = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump({'actualizado': ahora, 'p': precios}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'), sort_keys=True)
con = sum(1 for v in precios.values() if 'price' in v)
print(f'precios.json: {con} con stock · {len(precios) - con} sin stock · {errores} errores')
