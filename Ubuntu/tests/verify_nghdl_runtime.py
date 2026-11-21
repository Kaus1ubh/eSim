"""Exercise the installed simulators after an NGHDL installation."""
from configparser import ConfigParser
import os
from pathlib import Path
import re
import subprocess
import tempfile

source = Path(os.environ.get('NGHDL_SOURCE', '/opt/eSim-2.5/nghdl'))
evidence = Path('/tmp/task4-evidence')
evidence.mkdir(exist_ok=True)


def run(name, command, **kwargs):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120, **kwargs)
    (evidence / name).write_text(result.stdout + f'\nEXIT_CODE={result.returncode}\n')
    print(name, 'exit', result.returncode, result.stdout[-1500:], flush=True)
    assert result.returncode == 0, result.stdout[-3000:]
    return result.stdout


for tool in ['ghdl', 'verilator', 'ngspice']:
    flag = '-v' if tool == 'ngspice' else '--version'
    run('24-' + tool + '-version.log', [tool, flag])

config = ConfigParser()
assert config.read(Path.home() / '.nghdl/config.ini')
installed = Path(config.get('NGHDL', 'NGHDL_HOME'))
assert (installed / 'release/config.status').is_file()
assert Path(config.get('SRC', 'SRC_HOME')).resolve() == source.resolve()
assert Path('/usr/local/bin/nghdl').resolve() == (source / 'src/ngspice_ghdl.py').resolve()
assert Path('/usr/bin/ngspice').resolve() == (installed / 'install_dir/bin/ngspice').resolve()
print('NGHDL CONFIGURATION AND LAUNCHER LINKS PASSED', flush=True)

with tempfile.TemporaryDirectory(prefix='nghdl-runtime-') as tmp:
    tmp = Path(tmp)
    (tmp / 'inverter_tb.vhdl').write_text('''
library ieee;
use ieee.std_logic_1164.all;
entity inverter_tb is end;
architecture test of inverter_tb is
    signal i, o : std_logic;
begin
    dut: entity work.inverter port map(i => i, o => o);
    process
    begin
        i <= '0'; wait for 1 ns;
        assert o = '1' report "inverter failed for 0" severity failure;
        i <= '1'; wait for 1 ns;
        assert o = '0' report "inverter failed for 1" severity failure;
        report "VHDL_INVERTER_PASS";
        wait;
    end process;
end;
''')
    run('25-vhdl-analyze.log', ['ghdl', '-a', str(source / 'Example/logic_gates/inverter.vhdl'),
                              'inverter_tb.vhdl'], cwd=tmp)
    run('25-vhdl-elaborate.log', ['ghdl', '-e', 'inverter_tb'], cwd=tmp)
    output = run('25-vhdl-simulation.log',
                 ['ghdl', '-r', 'inverter_tb', '--assert-level=error', '--stop-time=3ns'], cwd=tmp)
    assert 'VHDL_INVERTER_PASS' in output

    (tmp / 'inverter.v').write_text('module inverter(input a, output o); assign o = ~a; endmodule\n')
    (tmp / 'sim.cpp').write_text('''
#include "Vinverter.h"
#include <cassert>
#include <iostream>
int main() {
    Vinverter dut;
    dut.a = 0; dut.eval(); assert(dut.o == 1);
    dut.a = 1; dut.eval(); assert(dut.o == 0);
    dut.final();
    std::cout << "VERILOG_INVERTER_PASS\\n";
}
''')
    run('26-verilog-generate.log', ['verilator', '--cc', 'inverter.v', '--exe', 'sim.cpp'], cwd=tmp)
    run('26-verilog-build.log', ['make', '-C', 'obj_dir', '-f', 'Vinverter.mk', '-j2'], cwd=tmp)
    output = run('26-verilog-simulation.log', [str(tmp / 'obj_dir/Vinverter')], cwd=tmp)
    assert 'VERILOG_INVERTER_PASS' in output

    (tmp / 'divider.cir').write_text('''Voltage divider
V1 in 0 DC 10
R1 in out 1k
R2 out 0 1k
.control
op
print v(out)
quit
.endc
.end
''')
    output = run('27-ngspice-divider.log', ['ngspice', '-b', 'divider.cir'], cwd=tmp)
    voltage = re.search(r'v\(out\)\s*=\s*([\d.eE+-]+)', output, re.IGNORECASE)
    assert voltage and abs(float(voltage.group(1)) - 5.0) < 1e-8, output

print('NGHDL RUNTIME CHECKS PASSED')
