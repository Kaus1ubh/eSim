"""Run focused, unmodified upstream installer paths inside Ubuntu 25.04.

Run in the disposable container, never on a working desktop.
"""
import os
from pathlib import Path
import subprocess

output = Path('/tmp/task4-evidence')
output.mkdir(exist_ok=True)

def capture(name, command, **kwargs):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, **kwargs)
    log = '$ ' + ' '.join(command) + '\n' + result.stdout
    log += f'\nEXIT_CODE={result.returncode}\n'
    (output / name).write_text(log)
    print(name, 'exit', result.returncode, flush=True)
    print(result.stdout[-1500:], flush=True)
    return result

capture('01-original-dispatcher.log', ['bash', '/tmp/original/install-eSim.sh', '--install'])
capture('02-environment.log', ['bash', '-c', 'cat /etc/os-release; python3 --version; dpkg-query -W python3-pyqt5 python3-matplotlib python3-psutil; apt-cache policy kicad'])
capture('03-system-imports.log', ['/usr/bin/python3', '-c', 'import psutil, matplotlib, PyQt5.QtWidgets; print("system imports OK")'])
capture('04-isolated-venv-create.log', ['python3', '-m', 'venv', '/tmp/isolated-env'])
capture('05-isolated-venv-imports.log', ['/tmp/isolated-env/bin/python', '-c', 'import psutil, matplotlib, PyQt5.QtWidgets'])

# Load only the original function definitions, without executing main or
# invoking KiCad/NGHDL/PDK installers. The function body is not modified.
source = Path('/tmp/original/install-eSim-25.04.sh').read_text()
functions = source.split('### Checking if file is passsed')[0]
home = Path('/tmp/original-home')
home.mkdir(exist_ok=True)
(home / '.esim').mkdir(exist_ok=True)
env = dict(os.environ, HOME=str(home), USER='root', DEBIAN_FRONTEND='noninteractive')
capture('06-original-dependencies.log', ['bash', '-c', functions + '\nset -eE\ntrap error_exit ERR\ninstallDependency\n'], env=env, input='y\n', timeout=600)
