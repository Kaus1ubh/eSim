# eSim 2.5 installer fixes for Ubuntu 25.04

**FOSSEE Winter Internship 2026, screening Task 4**

**Author:** Kaustubh, GitHub: Kaus1ubh

**Date:** 21 November 2026 (India Standard Time)

## Result

Four defects were reproduced in the installer branch and fixed:

1. The main installer cannot be parsed because an `if` block is not closed.
2. The eSim virtual environment cannot import the declared `psutil` dependency installed through apt.
3. Detecting an existing KiCad 8 installation exits the entire installer instead of continuing.
4. The script installs KiCad 8 but puts the custom symbol table in KiCad 6's configuration directory.

The focused checks pass after the changes. The actual eSim 2.5 main window also opens under Ubuntu 25.04 with the patched dependency environment. This is a partial installer repair and GUI smoke test. It does not establish that NGHDL, GHDL, Ngspice, KiCad integration, or a complete circuit simulation works.

## Sources and environment

The task requires investigating eSim 2.5 on Ubuntu 25.04 and submitting changes based on the `installers` branch. Two separate upstream inputs were used:

| Input | Exact reference |
|---|---|
| Installer branch baseline | `FOSSEE/eSim`, commit `a77d6b904c7bab275d819cf4d8cbb594802fe16d` |
| Official release | `https://static.fossee.in/esim/installation-files/eSim-2.5.zip` |
| Release SHA-256 | `b9860ae26f026930bae589520761f4a57b85d593a2e2cd1ac83d5e5db2f281ed` |
| OS | Ubuntu 25.04, Plucky Puffin, amd64, in Docker under WSL2 |
| Image digest | `ubuntu:25.04@sha256:27771fb7b40a58237c98e8d3e6b9ecdd9289cec69a857fccfb85ff36294dac20` |
| Python | 3.13.3 |
| Ubuntu PyQt5 | `5.15.11+dfsg-2` |
| Ubuntu Matplotlib | `3.8.3-7build1` |
| Ubuntu psutil | `5.9.8-2build3` |
| Resource limits | 2 CPUs, 3 GiB RAM |

The archive checksum matches the one published on the official downloads page. Windows and the existing Ubuntu 26.04 WSL installation were not used as substitutes for Ubuntu 25.04. Package installation and the GUI checks ran inside the disposable Ubuntu 25.04 container as root, with separate home directories for the original and patched virtual environments. A regular desktop user's permissions and desktop session were not tested.

The released archive and the installer branch have different entry scripts. The released entry script rejects Ubuntu 25.04 as unsupported. The installer branch already contains a 25.04 case and a version-specific script, but its entry script has a syntax error. The existing `Ubuntu/REPORT.md` documents earlier LLVM and Ubuntu support work by upstream contributors. Those changes are not claimed as part of this submission.

## 1. Main installer stops before doing any work

**File:** `Ubuntu/install-eSim.sh`, `run_version_script()`.

Running the original entry point produces:

```text
/tmp/original/install-eSim.sh: line 70: syntax error near unexpected token `}'
EXIT_CODE=2
```

The function opens `if [[ -f "$SCRIPT" ]]; then`, calls the version-specific installer, then contains copied configuration-writing statements. The closing `fi` is missing. Bash parses the function before invoking it, so no installation stage can run.

**Change:** Remove the misplaced configuration statements, close the conditional, and return the child's exit status. Report a missing child script as an error. Read version information from `/etc/os-release`, which also avoids depending on `lsb_release` on minimal Ubuntu installations. Preserve the existing 22.04 point-release selection by taking the first field of `VERSION`.

**Verification:** Both changed scripts pass `bash -n`. A temporary child script receives `--install` and exits with code 37; the real patched dispatcher returns 37. Removing the child causes the dispatcher to return 1 with a clear diagnostic. These child scripts are test fixtures, so the dispatch checks do not install packages.

The reproduction script records the syntax errors and dispatcher checks in its output directory.

## 2. A declared dependency is absent from the launch environment

**File:** `Ubuntu/install-eSim-scripts/install-eSim-25.04.sh`, `installDependency()`.

The original function creates an isolated virtual environment with `virtualenv`, installs `python3-psutil` through apt, then installs several other Python packages with pip inside the environment. The desktop launcher activates that environment. System Python can import psutil, while the launch interpreter cannot:

```text
$ /tmp/original-home/.esim/env/bin/python -c 'import psutil'
ModuleNotFoundError: No module named 'psutil'
EXIT_CODE=1
```

The original dependency function itself returns 0. This shows why a successful installer command is not enough to establish that its dependencies are accessible to the launch interpreter.

**Change:** Install the Ubuntu Python/Qt packages together, create the environment with `python3 -m venv --system-site-packages`, and install the remaining tools with that environment's explicit `python -m pip`. This makes Ubuntu's Qt, Matplotlib, and psutil packages visible and avoids downloading second copies of Qt and Matplotlib. Keep the environment rather than deleting it on reruns. Stop on a failed apt update instead of suppressing the failure. Finally, check the declared imports with the launch interpreter.

The existing upstream hdlparse source installation is retained, with its revision pinned to `e1153ace8ca1e25f9fb53350c41058ef8eb8dacf`. The redundant second hdlparse installation is removed. This is a reproducibility improvement; the original hdlparse installation succeeded in this investigation and is not counted as another reproduced failure.

**Verification:** The patched dependency function returns 0. The launch interpreter imports psutil, Matplotlib, PyQt5, hdlparse's Verilog parser, and watchdog. The psutil and Matplotlib paths resolve to `/usr/lib/python3/dist-packages/`.

**Scope of the defect:** The original eSim 2.5 main window also opens despite the missing psutil import. No psutil-dependent GUI failure was demonstrated. The claim here is that an explicitly installed dependency was inaccessible, not that this defect prevented startup.

The reproduction script records the original and patched dependency installation and import checks.

## 3. An existing KiCad installation prematurely ends setup

**File:** the 25.04 script, `installKicad()`.

When KiCad major version 8 is already present, the original function executes `exit 0`. Because functions execute in the installer's shell, this terminates the whole script. The subsequent symbol-library, NGHDL, PDK, and launcher stages are skipped even though the exit status indicates success.

**Change:** Use `return 0` to finish this function and allow the caller to continue.

**Verification:** Run the actual original and patched function definitions with command stubs reporting Ubuntu 25.04 and KiCad `8.0.8+dfsg-1`. A marker placed after the function call is absent before the fix and present afterwards. This is a control-flow regression test. It does not claim to install or launch real KiCad.


## 4. The symbol table goes into the wrong KiCad directory

**File:** the 25.04 script, `copyKicadLibrary()`.

The script's KiCad installer targets version 8, but the library function creates and copies `sym-lib-table` into `~/.config/kicad/6.0/`. KiCad 8 uses its own versioned configuration directory, so this copy does not configure its symbol table.

**Change:** Use `~/.config/kicad/8.0/` consistently in the version-specific installer. Uninstall removes only that version's `sym-lib-table`, preserving other KiCad 8 preferences and the KiCad 6 configuration.

**Verification:** Create a small compressed library fixture with a symbol table and a symbol file. Run each actual function with a temporary home directory containing an existing KiCad 6 table and KiCad 8 preferences. The extraction and copy commands run normally. The original writes the table under `6.0`; the patched function writes it under `8.0`. Calling the patched cleanup twice removes the installed table, preserves the existing configuration files, and succeeds on the second call. The test uses fixture library content and does not verify the complete eSim symbol collection inside KiCad.


## GUI startup check

The checksum-verified eSim 2.5 release was extracted into `/opt/eSim-2.5`. The script's real `createConfigFile()` function created the configuration. `tests/gui_smoke.py` then imported the release's `Application` module and constructed its actual main window using Qt's offscreen platform.

Both dependency environments produced:

```text
MAIN_WINDOW_TITLE=eSim-2.5
MAIN_WINDOW_VISIBLE=True
EXIT_CODE=0
```

The main toolbar, project pane, and status area render. The welcome browser is blank and logs a missing welcome-document path. Qt also reports limitations of the offscreen platform and system tray. These warnings remain unresolved. This test checks construction and rendering of the window, not an interactive desktop session or its external tools. The GUI check saves screenshots alongside its logs.

## Reproduction

Use a Linux or WSL shell with Docker and Git. From the repository root:

```bash
bash Ubuntu/tests/run-task4.sh
```

The runner builds the pinned Ubuntu image, retrieves the original scripts from the baseline Git commit, reproduces the original dependency behavior, and runs the focused checks. It saves results outside the checkout, in a timestamped directory under `../esim-task4-results/`, and removes its own test container on exit. Set `TASK4_OUTPUT` to choose another output directory. Network access to Ubuntu repositories, PyPI, and GitHub's codeload service is required.

To include the real GUI check, first download the official eSim 2.5 archive, then supply its absolute path:

```bash
ESIM_RELEASE_ZIP=/absolute/path/eSim-2.5.zip bash Ubuntu/tests/run-task4.sh
```

The runner verifies the archive checksum before extracting it. The complete runner was executed from a fresh image build with the official archive supplied. The baseline reproduction, focused regression checks, dependency installation, and both real GUI smoke checks completed successfully. An independent check also ran only the patched dependency function in a fresh container, without running the original installer first; installation and imports passed. Logs and screenshots are kept separately as submission evidence; generated output is not tracked in this repository.

For a desktop installation attempt, overlay `Ubuntu/install-eSim.sh` and `Ubuntu/install-eSim-scripts/` onto the extracted release folder, then run `bash install-eSim.sh --install` from that folder. The version-specific installer still performs system package installation and includes upstream removal operations. Use a disposable Ubuntu 25.04 VM for further complete-install testing.

## Remaining work and limits

- The official eSim 2.5 archive's bundled `nghdl/install-nghdl.sh` supports 22.04, 23.04, and 24.04, but has no 25.04 dispatch case. On 25.04 it reaches the unsupported-version error. This is a known remaining blocker to complete installation; these eSim installer fixes do not add NGHDL support.
- Complete installation through KiCad's PPA, NGHDL/GHDL compilation, SKY130 installation, desktop shortcut creation, and an actual circuit simulation was not attempted after these repairs.
- The KiCad PPA addition and its exact package pin are unchanged. Ubuntu's configured repositories offered `8.0.8+dfsg-1` during the checks, but the PPA path was not validated.
- The LLVM/GHDL issues described in upstream's existing report were not independently reproduced or repaired here.
- Python tools other than hdlparse remain unpinned, so future dependency resolution may change. Giving the environment access to Ubuntu packages also means their versions follow apt updates.
- GUI checks used an offscreen Qt platform as root. Native desktop integration, non-root permissions, other Ubuntu versions, and ARM were not tested.
- `.gitattributes` enforces LF line endings for shell scripts to keep Windows checkouts usable in Bash.

## References

- [Official Task 4 description](https://esim.fossee.in/internship)
- [Official releases and checksums](https://esim.fossee.in/downloads)
- [Installer baseline](https://github.com/FOSSEE/eSim/tree/a77d6b904c7bab275d819cf4d8cbb594802fe16d/Ubuntu)
- [Python virtual environment behavior](https://docs.python.org/3/library/venv.html)
- [Pinned upstream hdlparse source](https://github.com/hdl/pyHDLParser/tree/e1153ace8ca1e25f9fb53350c41058ef8eb8dacf)
