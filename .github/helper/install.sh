#!/bin/bash

export PIP_ROOT_USER_ACTION=ignore

set -e

# act runs workflow steps as root; bench refuses root. Re-run this script as ubuntu.
if [[ "${ACT:-}" == "true" && "$(id -u)" -eq 0 ]]; then
	mkdir -p /home/ubuntu
	chown ubuntu:ubuntu /home/ubuntu
	exec runuser -u ubuntu -- env \
		HOME=/home/ubuntu \
		ACT=true \
		BRANCH_NAME="${BRANCH_NAME:-}" \
		GITHUB_WORKSPACE="${GITHUB_WORKSPACE}" \
		PIP_ROOT_USER_ACTION=ignore \
		PATH="${PATH}" \
		bash "$0"
fi

# Check for merge conflicts before proceeding
if [[ "${ACT:-}" != "true" ]]; then
	python -m compileall -f "${GITHUB_WORKSPACE}"
fi
if grep -lr --exclude-dir=node_modules "^<<<<<<< " "${GITHUB_WORKSPACE}"
    then echo "Found merge conflicts"
    exit 1
fi

cd ~ || exit

pip install --upgrade pip
pip install frappe-bench

mysql --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL character_set_server = 'utf8mb4'"
mysql --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

mysql --host 127.0.0.1 --port 3306 -u root -e "CREATE OR REPLACE DATABASE test_site"
mysql --host 127.0.0.1 --port 3306 -u root -e "CREATE OR REPLACE USER 'test_site'@'localhost' IDENTIFIED BY 'test_site'"
mysql --host 127.0.0.1 --port 3306 -u root -e "GRANT ALL PRIVILEGES ON \`test_site\`.* TO 'test_site'@'localhost'"

mysql --host 127.0.0.1 --port 3306 -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'"  # match site_cofig
mysql --host 127.0.0.1 --port 3306 -u root -e "FLUSH PRIVILEGES"

git clone https://github.com/frappe/frappe --branch "version-15"
bench init frappe-bench --frappe-path ~/frappe --python "$(which python)" --skip-assets --ignore-exist

cp "${GITHUB_WORKSPACE}/.github/helper/common_site_config.json" ~/frappe-bench/sites/common_site_config.json

mkdir ~/frappe-bench/sites/test_site
cp -r "${GITHUB_WORKSPACE}/.github/helper/site_config.json" ~/frappe-bench/sites/test_site/

cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile
sed -i 's/^redis_cache:/# redis_cache:/g' Procfile
sed -i 's/^redis_queue:/# redis_queue:/g' Procfile

wait_for_redis() {
	local port="${REDIS_PORT:-6379}"
	for _ in $(seq 1 60); do
		if (echo > /dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
			return 0
		fi
		sleep 1
	done
	echo "Redis service did not become reachable on port ${port}" >&2
	return 1
}

bench get-app erpnext https://github.com/frappe/erpnext --branch "version-15" --resolve-deps --skip-assets
bench get-app beam "${GITHUB_WORKSPACE}" --skip-assets

printf '%s\n' 'frappe' 'erpnext' 'beam' > ~/frappe-bench/sites/apps.txt
bench setup requirements --python
bench use test_site

wait_for_redis
bench --site test_site reinstall --yes --admin-password admin

bench --site test_site migrate
bench --site test_site build

# Python test deps from each app's [tool.bench.dev-dependencies] (beam: pytest*, pycups, test_utils, pytest-playwright).
# Playwright browser binaries still need `python -m playwright install`, which the
# workflow's Run Tests step does.
bench setup requirements --dev

echo "BENCH VERSION NUMBERS:"
bench version
echo "SITE LIST-APPS:"
bench list-apps

bench execute 'beam.tests.setup.before_test'
