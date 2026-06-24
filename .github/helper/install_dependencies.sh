#!/bin/bash

# Check for merge conflicts before proceeding
if [[ "${ACT:-}" != "true" ]]; then
	python -m compileall -f "${GITHUB_WORKSPACE}"
fi
if grep -lr --exclude-dir=node_modules "^<<<<<<< " "${GITHUB_WORKSPACE}"
    then echo "Found merge conflicts"
    exit 1
fi

# redis-server binary is required for `bench init` version detection; runtime Redis is the workflow service.
sudo apt update -y && sudo apt install redis-server cups libcups2-dev mariadb-client cron -y
