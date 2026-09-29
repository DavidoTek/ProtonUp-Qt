"""Strip a PySide6 wheel installation down to what ProtonUp-Qt needs.

Keeps the listed Python modules and Qt plugins, then keeps only the Qt libraries that
are (transitively) needed by them. Prints the external libraries expected on the host.

Usage: prune-pyside6.py <site-packages>
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = {'QtCore', 'QtGui', 'QtWidgets', 'QtDBus', 'QtUiTools'}

PLUGINS = {
    'platforms': ['libqxcb.so', 'libqwayland.so', 'libqoffscreen.so', 'libqminimal.so'],
    'platformthemes': None,
    'platforminputcontexts': ['libcomposeplatforminputcontextplugin.so', 'libibusplatforminputcontextplugin.so'],
    'imageformats': ['libqgif.so', 'libqico.so', 'libqjpeg.so', 'libqsvg.so', 'libqwebp.so'],
    'iconengines': None,
    'xcbglintegrations': None,
    'wayland-decoration-client': None,
    'wayland-graphics-integration-client': ['libqt-plugin-wayland-egl.so'],
    'wayland-shell-integration': ['libxdg-shell.so'],
}


def needed(path: Path) -> list[str]:
    out = subprocess.run(['readelf', '-dW', str(path)], capture_output=True, text=True, check=True).stdout
    return [line.split('[', 1)[1].rstrip(']') for line in out.splitlines() if '(NEEDED)' in line]


def remove(path: Path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


site = Path(sys.argv[1])
pyside = site / 'PySide6'
qt = pyside / 'Qt'
qtlib = qt / 'lib'

# Python modules, type stubs and developer tools
for entry in pyside.iterdir():
    is_module = entry.name.startswith('Qt') and entry.name.endswith('.abi3.so')
    is_tool = entry.is_file() and entry.suffix == '' and os.access(entry, os.X_OK)
    if entry.suffix == '.pyi' or is_tool or (is_module and entry.name.split('.', 1)[0] not in MODULES):
        remove(entry)
for name in ('include', 'typesystems', 'glue', 'scripts', 'doc', 'lib'):
    if (pyside / name).exists():
        remove(pyside / name)
# Only needed by QtQml; it would pull in QtQml and QtNetwork (and with that Kerberos)
for lib in pyside.glob('libpyside6qml*'):
    remove(lib)

# Qt data that is not needed at runtime
for name in ('qml', 'metatypes', 'libexec'):
    if (qt / name).exists():
        remove(qt / name)

# Translations of Qt tools
for qm in (qt / 'translations').glob('*.qm'):
    if not qm.name.startswith('qt'):
        remove(qm)

# Qt plugins
for category in (qt / 'plugins').iterdir():
    if category.name not in PLUGINS:
        remove(category)
        continue
    keep = PLUGINS[category.name]
    if keep is not None:
        for plugin in category.iterdir():
            if plugin.name not in keep:
                remove(plugin)

# Qt libraries: keep the dependency closure of modules and plugins
bundled = {p.name for p in qtlib.iterdir()} | {p.name for p in pyside.glob('lib*.so*')} | {p.name for p in (site / 'shiboken6').glob('lib*.so*')}
queue = [p for p in pyside.glob('*.so*')] + [p for p in (site / 'shiboken6').glob('*.so*')] + list((qt / 'plugins').rglob('*.so'))
seen, keep, external = set(), set(), set()
while queue:
    path = queue.pop()
    if path in seen:
        continue
    seen.add(path)
    for lib in needed(path):
        if lib in bundled:
            if (qtlib / lib).exists() and lib not in keep:
                keep.add(lib)
                queue.append(qtlib / lib)
        else:
            external.add(lib)
for lib in qtlib.iterdir():
    if lib.name not in keep:
        remove(lib)

print('Kept Qt libraries:', ' '.join(sorted(keep)))
print('External libraries:', ' '.join(sorted(external)))
