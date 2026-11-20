"""Focused regression checks. Run only inside the disposable Ubuntu 25.04 container."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

assert 'VERSION_ID="25.04"' in Path('/etc/os-release').read_text()
ROOT = Path('/tmp/patched')
ORIGINAL = Path('/tmp/original/install-eSim-25.04.sh')
PATCHED = ROOT / 'install-eSim-scripts/install-eSim-25.04.sh'
EVIDENCE = Path('/tmp/task4-evidence')
EVIDENCE.mkdir(exist_ok=True)

def run(name, command, **kwargs):
    started = time.monotonic()
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=600, **kwargs)
    elapsed = time.monotonic() - started
    (EVIDENCE / name).write_text('$ ' + ' '.join(command) + '\n' + result.stdout
                                + f'\nEXIT_CODE={result.returncode}\nSECONDS={elapsed:.3f}\n')
    print(name, 'exit', result.returncode, f'{elapsed:.2f}s', flush=True)
    print(result.stdout[-1200:], flush=True)
    return result

def functions(path):
    return path.read_text().split('### Checking if file is passsed')[0]

def shell(name, source, extra, **kwargs):
    script = EVIDENCE / (name + '.sh')
    script.write_text(functions(source) + '\n' + extra)
    return run(name + '.log', ['bash', str(script)], **kwargs)

for path in [ROOT / 'install-eSim.sh', PATCHED]:
    result = run('07-syntax-' + path.name + '.log', ['bash', '-n', str(path)])
    assert result.returncode == 0

# The real entry point must forward the child exit status and reject a missing child.
with tempfile.TemporaryDirectory(prefix='dispatcher-') as tmp:
    tmp = Path(tmp)
    dispatcher = tmp / 'install-eSim.sh'
    shutil.copyfile(ROOT / 'install-eSim.sh', dispatcher)
    child = tmp / 'install-eSim-scripts/install-eSim-25.04.sh'
    child.parent.mkdir()
    child.write_text('echo "CHILD_ARGUMENT=$1"\nexit 37\n')
    result = run('08-dispatch-status.log', ['bash', str(dispatcher), '--install'])
    assert result.returncode == 37 and 'CHILD_ARGUMENT=--install' in result.stdout
    child.unlink()
    result = run('09-dispatch-missing-child.log', ['bash', str(dispatcher), '--install'])
    assert result.returncode == 1 and 'not found' in result.stdout

# External commands are stubs here: this checks control flow with KiCad 8 present.
stub = '''
lsb_release() { echo 25.04; }
dpkg() { return 0; }
dpkg-query() { echo 8.0.8+dfsg-1; }
installKicad
echo CONTINUED_AFTER_KICAD
'''
before = shell('10-original-kicad-return', ORIGINAL, stub)
after = shell('11-patched-kicad-return', PATCHED, stub)
assert 'CONTINUED_AFTER_KICAD' not in before.stdout
assert after.returncode == 0 and 'CONTINUED_AFTER_KICAD' in after.stdout

# Exercise the actual extraction/copy operations with a tiny symbol library.
for label, source in [('original', ORIGINAL), ('patched', PATCHED)]:
    with tempfile.TemporaryDirectory(prefix='symbols-') as tmp:
        tmp = Path(tmp)
        (tmp / 'library').mkdir()
        with tarfile.open(tmp / 'library/kicadLibrary.tar.xz', 'w:xz') as archive:
            for name, data in [('template/sym-lib-table', b'(sym_lib_table)\n'),
                               ('eSim-symbols/task4-test.kicad_sym', b'test\n')]:
                info = tarfile.TarInfo('kicadLibrary/' + name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        home = tmp / 'home'
        home.mkdir()
        previous = home / '.config/kicad/6.0/sym-lib-table'
        previous.parent.mkdir(parents=True)
        previous.write_text('existing KiCad 6 table\n')
        preferences = home / '.config/kicad/8.0/kicad_common.json'
        preferences.parent.mkdir(parents=True)
        preferences.write_text('{}\n')
        env = dict(os.environ, HOME=str(home), USER='root')
        result = shell('12-' + label + '-symbols', source,
                       'set -eE\nmkdir -p /usr/share/kicad/symbols\ncopyKicadLibrary\n',
                       cwd=tmp, env=env)
        assert result.returncode == 0
        correct = (home / '.config/kicad/8.0/sym-lib-table').is_file()
        assert correct == (label == 'patched')
        if label == 'patched':
            result = shell('12-patched-symbol-cleanup', source,
                           'set -eE\nremoveKicadLibrary\nremoveKicadLibrary\n', env=env)
            assert result.returncode == 0
            assert not (home / '.config/kicad/8.0/sym-lib-table').exists()
            assert previous.read_text() == 'existing KiCad 6 table\n'
            assert preferences.read_text() == '{}\n'

result = run('13-original-launcher-imports.log',
             ['/tmp/original-home/.esim/env/bin/python', '-c', 'import psutil'])
assert result.returncode != 0 and 'psutil' in result.stdout

home = Path('/tmp/patched-home')
home.mkdir(exist_ok=True)
env = dict(os.environ, HOME=str(home), USER='root', DEBIAN_FRONTEND='noninteractive')
result = shell('14-patched-dependencies', PATCHED,
               'set -eE\ntrap error_exit ERR\ninstallDependency\n', env=env)
assert result.returncode == 0
result = run('15-patched-launcher-imports.log', [str(home / '.esim/env/bin/python'), '-c',
             'import psutil, matplotlib, PyQt5.QtWidgets, hdlparse.verilog_parser, watchdog; '
             'print("All GUI dependency imports OK"); '
             'print("psutil:", psutil.__file__); print("matplotlib:", matplotlib.__file__)'], env=env)
assert result.returncode == 0
print('ALL FOCUSED CHECKS PASSED', flush=True)
