"""Check the compatibility patch against the NGHDL bundled with eSim 2.5."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

release = Path(os.environ.get('ESIM_RELEASE_DIR', '/opt/eSim-2.5'))
patch = Path('/tmp/patched/install-eSim-scripts/nghdl-25.04.patch')
evidence = Path('/tmp/task4-evidence')
evidence.mkdir(exist_ok=True)
assert 'VERSION_ID="25.04"' in Path('/etc/os-release').read_text()


def run(name, command, **kwargs):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30, **kwargs)
    (evidence / name).write_text(result.stdout + f'\nEXIT_CODE={result.returncode}\n')
    print(name, 'exit', result.returncode, result.stdout, flush=True)
    return result


with tempfile.TemporaryDirectory(prefix='nghdl-check-') as tmp:
    tmp = Path(tmp)
    with zipfile.ZipFile(release / 'nghdl.zip') as archive:
        archive.extractall(tmp)
    source = tmp / 'nghdl'
    dispatcher = source / 'install-nghdl.sh'
    result = run('18-original-nghdl-dispatch.log', ['bash', str(dispatcher), '--install'])
    assert result.returncode == 1 and 'Unsupported Ubuntu version: 25.04' in result.stdout
    result = run('19-nghdl-patch.log',
                 ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(patch)], cwd=source)
    assert result.returncode == 0
    for path in [dispatcher, source / 'install-nghdl-scripts/install-nghdl-24.04.sh']:
        result = run('20-syntax-' + path.name + '.log', ['bash', '-n', str(path)])
        assert result.returncode == 0

    # Check dispatch and failure propagation without compiling the simulators.
    child = source / 'install-nghdl-scripts/install-nghdl-24.04.sh'
    child.write_text('echo "NGHDL_ARGUMENT=$1"\nexit 37\n')
    for argument in ['--install', '--uninstall']:
        result = run('21-nghdl-' + argument[2:] + '-dispatch.log',
                     ['bash', str(dispatcher), argument])
        assert result.returncode == 37 and 'NGHDL_ARGUMENT=' + argument in result.stdout
    child.unlink()
    result = run('22-nghdl-missing-child.log', ['bash', str(dispatcher), '--install'])
    assert result.returncode == 1 and 'not found' in result.stdout
    result = run('23-nghdl-invalid-option.log', ['bash', str(dispatcher), '--invalid'])
    assert result.returncode == 1 and 'Invalid argument' in result.stdout
print('NGHDL PATCH CHECKS PASSED')

if '--install' in sys.argv:
    destination = release / 'install-eSim-scripts'
    destination.mkdir(exist_ok=True)
    shutil.copyfile(patch, destination / patch.name)
    installer = Path('/tmp/patched/install-eSim-scripts/install-eSim-25.04.sh')
    functions = installer.read_text().split('### Checking if file is passsed')[0]
    with (evidence / '24-nghdl-install.log').open('w') as log:
        result = subprocess.run(['bash', '-c', functions + '\nset -eE\ntrap error_exit ERR\ninstallNghdl\n'],
                                cwd=release, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    assert result.returncode == 0, 'NGHDL installation failed; see 24-nghdl-install.log'
    print('NGHDL INSTALLATION PASSED')
