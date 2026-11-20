"""Compare the release GUI with original and patched dependency environments."""
import os
from pathlib import Path
import subprocess

evidence = Path('/tmp/task4-evidence')
release = Path('/opt/eSim-2.5')
source = Path('/tmp/patched/install-eSim-scripts/install-eSim-25.04.sh').read_text()
functions = source.split('### Checking if file is passsed')[0]
home = Path('/tmp/patched-home')
env = dict(os.environ, HOME=str(home), USER='root', QT_QPA_PLATFORM='offscreen')
result = subprocess.run(['bash', '-c', functions + '\nset -eE\ncreateConfigFile\n'],
                        cwd=release, env=env, text=True, capture_output=True)
assert result.returncode == 0, result.stderr
for label, python in [('original', '/tmp/original-home/.esim/env/bin/python'),
                      ('patched', str(home / '.esim/env/bin/python'))]:
    env['TASK4_ENV'] = label
    result = subprocess.run([python, '/tmp/gui_smoke.py'], cwd=release / 'src/frontEnd',
                            env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=45)
    (evidence / ('16-' + label + '-gui.log')).write_text(result.stdout + f'\nEXIT_CODE={result.returncode}\n')
    print(label, 'GUI exit', result.returncode, result.stdout, flush=True)
    assert result.returncode == 0
