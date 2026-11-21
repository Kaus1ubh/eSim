#!/usr/bin/env bash
# Run from a Linux/WSL shell with Docker and Git available.
set -euo pipefail
repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
baseline=a77d6b904c7bab275d819cf4d8cbb594802fe16d
output=${TASK4_OUTPUT:-"$(dirname "$repo")/esim-task4-results/$(date +%Y%m%d-%H%M%S)"}
container="esim-task4-verify-$$"
if [[ ${NGHDL_INTEGRATION:-0} == 1 && -z ${ESIM_RELEASE_ZIP:-} ]]; then
    echo 'NGHDL_INTEGRATION requires ESIM_RELEASE_ZIP.' >&2
    exit 1
fi
mkdir -p "$output/original"
git -C "$repo" show "$baseline:Ubuntu/install-eSim.sh" > "$output/original/install-eSim.sh"
git -C "$repo" show "$baseline:Ubuntu/install-eSim-scripts/install-eSim-25.04.sh" > "$output/original/install-eSim-25.04.sh"
docker build -t esim-task4-verifier -f "$repo/Ubuntu/tests/Dockerfile.task4" "$repo"
docker run --name "$container" --cpus 2 --memory 3g -d esim-task4-verifier
cleanup() {
    docker cp "$container:/tmp/task4-evidence" "$output/evidence" || true
    docker rm -f "$container" >/dev/null
}
trap cleanup EXIT
docker cp "$output/original/." "$container:/tmp/original"
docker exec "$container" python3 /tmp/patched/tests/capture_baseline.py
docker exec "$container" python3 /tmp/patched/tests/verify_task4.py

# Optional: validate the real release GUI with both dependency environments.
if [[ -n ${ESIM_RELEASE_ZIP:-} ]]; then
    echo 'b9860ae26f026930bae589520761f4a57b85d593a2e2cd1ac83d5e5db2f281ed  '"$ESIM_RELEASE_ZIP" | sha256sum -c -
    docker cp "$ESIM_RELEASE_ZIP" "$container:/tmp/eSim-2.5.zip"
    docker exec "$container" python3 -m zipfile -e /tmp/eSim-2.5.zip /opt
    if [[ ${NGHDL_INTEGRATION:-0} == 1 ]]; then
        docker exec -e NGHDL_BUILD_JOBS="${NGHDL_BUILD_JOBS:-2}" "$container" \
            python3 /tmp/patched/tests/verify_nghdl.py --install
        docker exec "$container" python3 /tmp/patched/tests/verify_nghdl_runtime.py
    else
        docker exec "$container" python3 /tmp/patched/tests/verify_nghdl.py
    fi
    docker cp "$repo/Ubuntu/tests/gui_smoke.py" "$container:/tmp/gui_smoke.py"
    docker exec "$container" python3 /tmp/patched/tests/capture_gui.py
fi
echo "Checks passed. Evidence will be saved under $output/evidence."
