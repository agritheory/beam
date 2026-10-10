#!/usr/bin/env bash
set -euo pipefail

BENCH_ROOT="${BENCH_ROOT:-/home/runner/frappe-bench}"
BENCH_PORT="${BENCH_PORT:-8000}"
PING_URL="http://127.0.0.1:${BENCH_PORT}/api/method/ping"

curl_ping() {
	curl -sf --connect-timeout 2 "$PING_URL" >/dev/null 2>&1
}

run_as_bench_user() {
	local command="$1"
	if [[ "${ACT:-}" == "true" && "$(id -u)" -eq 0 ]]; then
		runuser -u ubuntu -- env HOME=/home/ubuntu bash -lc "cd '${BENCH_ROOT}' && ${command}"
	else
		bash -lc "cd '${BENCH_ROOT}' && ${command}"
	fi
}

if curl_ping; then
	exit 0
fi

run_as_bench_user "nohup bench serve --port ${BENCH_PORT} >> bench_run_logs.txt 2>&1 &"
sleep 3

for _ in $(seq 1 60); do
	if curl_ping; then
		exit 0
	fi
	sleep 2
done

echo "bench web not ready at ${PING_URL}" >&2
tail -80 "${BENCH_ROOT}/bench_run_logs.txt" 2>/dev/null || true
exit 56
