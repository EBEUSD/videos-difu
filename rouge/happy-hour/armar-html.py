"""Vuelve a meter banner-happy-hour.js (codificado en base64) dentro de banner-happy-hour.html.
Usar cada vez que se edite el .js:  python armar-html.py
Versión elegante:                    python armar-html.py elegante
(El editor de VTEX borra las etiquetas <script>, por eso el código va codificado en una imagen oculta.)"""
import base64, os, re, sys

aqui = os.path.dirname(os.path.abspath(__file__))
base = 'banner-happy-hour' + ('-' + sys.argv[1] if len(sys.argv) > 1 else '')
js = open(os.path.join(aqui, base + '.js'), encoding='utf-8').read()
html_path = os.path.join(aqui, base + '.html')
html = open(html_path, encoding='utf-8').read()
b64 = base64.b64encode(js.rstrip('\n').encode('utf-8')).decode()
html, n = re.subn(r'(id="hh-boot"[^>]*?data-c=")[^"]*(")', lambda m: m.group(1) + b64 + m.group(2), html, flags=re.S)
if n != 1:
    raise SystemExit('No encontré la imagen hh-boot en el HTML')
open(html_path, 'w', encoding='utf-8').write(html)
print(base + '.html actualizado')
