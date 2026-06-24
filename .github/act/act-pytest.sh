#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# act bind-mounts the repo; earlier root steps may leave root-owned __pycache__ dirs.
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Prefer ~/.local/bin/act over an older ~/bin/act install.
export PATH="${HOME}/.local/bin:${PATH}"
hash -r 2>/dev/null || true

DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"
GITHUB_TOKEN="${GITHUB_TOKEN:-${ghpat:-$(gh auth token 2>/dev/null || true)}}"

if [[ -z "${GITHUB_TOKEN}" ]]; then
	echo "Set GITHUB_TOKEN or ghpat before running." >&2
	exit 1
fi

ACT_VERSION="$(act --version 2>/dev/null | awk '{print $3}')"
MIN_ACT_VERSION="0.2.81"
if [[ -n "${ACT_VERSION}" ]] \
	&& [[ "$(printf '%s\n' "${MIN_ACT_VERSION}" "${ACT_VERSION}" | sort -V | head -1)" != "${MIN_ACT_VERSION}" ]]; then
	echo "act ${ACT_VERSION} is too old for node24 actions; install act >= ${MIN_ACT_VERSION}." >&2
	echo "  curl -sL https://github.com/nektos/act/releases/download/v0.2.89/act_Linux_x86_64.tar.gz | tar -xz -C ~/.local/bin act" >&2
	exit 1
fi

# act-latest has no passwordless sudo for ubuntu; run the job as root for apt/sudo steps.
# install.sh re-execs bench setup as ubuntu. Map test_site via docker --add-host below.
ACT_RUNNER_IMAGE="${ACT_RUNNER_IMAGE:-catthehacker/ubuntu:act-latest}"
ACT_PULL_ARGS=(--pull=false)
if ! docker image inspect "${ACT_RUNNER_IMAGE}" >/dev/null 2>&1; then
	echo "Runner image ${ACT_RUNNER_IMAGE} not found locally; pulling once..." >&2
	ACT_PULL_ARGS=(--pull=true)
fi

exec act pull_request \
	-W .github/workflows/pytest.yaml \
	-j tests \
	-e .github/act/pull_request.json \
	-s "GITHUB_TOKEN=${GITHUB_TOKEN}" \
	--actor "$(gh api user -q .login 2>/dev/null || echo nektos)" \
	-P "ubuntu-latest=${ACT_RUNNER_IMAGE}" \
	"${ACT_PULL_ARGS[@]}" \
	--container-architecture linux/amd64 \
	--env BENCH_ROOT=/home/ubuntu/frappe-bench \
	--env BEAM_TEST_TELEMETRY=true \
	--env BEAM_TEST_STACK_DUMP_SECONDS=60 \
	--env BEAM_CUPS_HOST=cups \
	--env BEAM_CUPS_PORT=631 \
	--container-options "--group-add ${DOCKER_GID} --add-host test_site:127.0.0.1" \
	"$@"
