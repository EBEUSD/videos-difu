"""Actualiza el laboratorio de punta a punta: perfumes nuevos de VTEX, SKUs, precios y los archivos del tema.

Uso (desde cualquier carpeta):
  python herramientas/actualizar-todo.py                 regenera todo y pregunta si sube propuestas a GitHub
  python herramientas/actualizar-todo.py --excel ARCHIVO también rearma los perfumes de nicho desde el Excel
  python herramientas/actualizar-todo.py --sin-subir     regenera todo y no sube nada

El tema de Rouge solo se regenera en la carpeta local: después hay que volver a lanzar `vtex link` (o hacer el PR).
En GitHub se suben únicamente los archivos del laboratorio, nunca otros cambios del repositorio."""
import os, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8')

aqui = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(aqui)
REPO = os.path.abspath(os.path.join(LAB, '..', '..'))
SUBIR = ['catalogo.json', 'compartir.jpg', 'catalogo-nicho.json', 'precios.json', 'herramientas', 'imagenes', 'arma-perfume-notas.html']


def correr(nombre, *args):
    print('\n▶', nombre, *args, flush=True)
    r = subprocess.run([sys.executable, os.path.join(aqui, nombre), *args], cwd=LAB,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    if r.returncode:
        raise SystemExit('✖ Falló %s: no se siguió con los pasos siguientes.' % nombre)


def git(*args, salida=False):
    r = subprocess.run(['git', *args], cwd=REPO, capture_output=salida, text=True, encoding='utf-8')
    if r.returncode:
        raise SystemExit('✖ git %s falló%s' % (' '.join(args), (': ' + (r.stderr or '').strip()) if salida else ''))
    return (r.stdout or '').strip() if salida else ''


if '--excel' in sys.argv:
    xlsx = os.path.abspath(sys.argv[sys.argv.index('--excel') + 1])
    correr('catalogo-desde-excel.py', xlsx, 'catalogo-nicho.json')
correr('catalogo-desde-vtex.py')
correr('actualizar-skus.py')
correr('actualizar-precios.py')
correr('armar-vtex.py')

rutas = [os.path.relpath(os.path.join(LAB, f), REPO).replace(os.sep, '/') for f in SUBIR]
git('add', '--', *rutas)
cambios = git('diff', '--cached', '--stat', salida=True)
if not cambios:
    print('\n✔ Listo. No hubo cambios en el laboratorio.')
    raise SystemExit
print('\nCambios del laboratorio:\n' + cambios)

if '--sin-subir' in sys.argv:
    git('reset', '-q', '--', *rutas)
    print('\n✔ Listo. Quedó todo local (sin subir).')
    raise SystemExit
if input('\n¿Subir propuestas a GitHub? (s/n) ').strip().lower() not in ('s', 'si', 'sí'):
    git('reset', '-q', '--', *rutas)
    print('✔ Listo. No se subió nada.')
    raise SystemExit

git('commit', '-q', '-m', 'Laboratorio de notas: catálogo y precios actualizados', '--', *rutas)
git('pull', '--rebase', '--autostash', '-q', '-X', 'theirs')
git('push', '-q')
print('✔ Subido. GitHub Pages lo publica en uno o dos minutos.')
print('  Para verlo en VTEX: cortá `vtex link` y volvé a lanzarlo.')
