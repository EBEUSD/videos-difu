"""Guarda en catalogo.json el SKU y vendedor de cada perfume (el más barato con stock hoy),
para que el botón funcione aunque el Sandbox de VTEX no deje consultar la API en vivo.
Uso:  python herramientas/actualizar-skus.py        (desde la carpeta laboratorio-notas)
catalogo-desde-vtex.py ya lo hace al armar el catálogo; esto sirve para refrescarlo sin rearmarlo."""
import json, os, sys, time, urllib.request

aqui = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(aqui, '..', 'catalogo.json')
API = 'https://www.perfumeriasrouge.com/api/catalog_system/pub/products/search?'

P = json.load(open(CATALOGO, encoding='utf-8'))
ok = sin = err = 0
for i in range(0, len(P), 50):
    lote = P[i:i + 50]
    q = '&'.join('fq=productId:' + p['id'] for p in lote) + '&_from=0&_to=49'
    try:
        req = urllib.request.Request(API + q, headers={'User-Agent': 'laboratorio-notas'})
        datos = {d['productId']: d for d in json.load(urllib.request.urlopen(req, timeout=40))}
    except Exception as e:
        err += len(lote); print('error', e, file=sys.stderr); continue
    for p in lote:
        best = None
        for it in datos.get(p['id'], {}).get('items', []):
            for s in it.get('sellers', []):
                c = s.get('commertialOffer', {})
                if c.get('AvailableQuantity', 0) > 0 and c.get('Price', 0) > 0 and (not best or c['Price'] < best[0]):
                    best = (c['Price'], it['itemId'], s['sellerId'])
        p.pop('sku', None); p.pop('sel', None)
        if best:
            p['sku'], p['sel'] = best[1], best[2]; ok += 1
        else:
            sin += 1
    time.sleep(0.2)
json.dump(P, open(CATALOGO, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'con SKU: {ok} · sin stock: {sin} · errores: {err}')
