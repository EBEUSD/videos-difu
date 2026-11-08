"""Genera arma-perfume-notas-SANDBOX.html (el que se pega en el Sandbox de VTEX) a partir de arma-perfume-notas.html.
El editor de VTEX borra las etiquetas <script>: acá todo el código se codifica en base64 dentro de una imagen
oculta que lo ejecuta al cargar (mismo truco que rouge/etiquetas y rouge/happy-hour).
Uso:  python herramientas/armar-sandbox.py        (desde la carpeta laboratorio-notas)
Se edita siempre arma-perfume-notas.html (legible) y después se vuelve a correr esto."""
import base64, os, re

aqui = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(aqui, '..', 'arma-perfume-notas.html')
OUT = os.path.join(aqui, '..', 'arma-perfume-notas-SANDBOX.html')

html = open(SRC, encoding='utf-8').read()
html = re.sub(r'<!--.*?-->', '', html, flags=re.S)   # los comentarios pueden mencionar <script>
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
if not scripts:
    raise SystemExit('No encontré etiquetas <script> en el HTML')
# cada bloque va en base64 por separado y se ejecuta en el ámbito global, como su propia etiqueta <script>
def b64(t):
    return base64.b64encode(t.encode('utf-8')).decode()
datos = ' '.join('data-c%d="%s"' % (i, b64(s)) for i, s in enumerate(scripts))
boot = ('<!-- Código en base64: el CMS borra las etiquetas script; lo arranca el onerror de la imagen.\n'
        '     NO editar acá: editar arma-perfume-notas.html y correr herramientas/armar-sandbox.py -->\n'
        '<img id="ap-boot" src="x" alt="" style="display:none" ' + datos + '\n'
        '    onerror="if(!window.apRun){window.apRun=1;for(var i=0,c;(c=this.getAttribute(\'data-c\'+i));i++){try{(0,eval)(decodeURIComponent(escape(atob(c))))}catch(e){console.error(\'laboratorio:\',e)}}}">\n'
        '<svg width="0" height="0" style="position:absolute" onload="var i=document.getElementById(\'ap-boot\');if(i)if(i.onerror)i.onerror.call(i)"></svg>\n')
sin_scripts = html
sin_scripts = re.sub(r'<script>.*?</script>\s*', '', sin_scripts, flags=re.S)
sin_scripts = sin_scripts.replace('</body>', boot + '</body>', 1)
open(OUT, 'w', encoding='utf-8').write(sin_scripts)
print('Generado', os.path.basename(OUT), '·', round(len(sin_scripts.encode('utf-8')) / 1024), 'KB ·', len(scripts), 'bloques de código')
