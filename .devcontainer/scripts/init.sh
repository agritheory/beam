#!bin/bash

echo "Building Devcontainer from branch: " 
branch_name=$(git rev-parse --abbrev-ref HEAD)
echo $branch_name

set -e

if [[ -f "/workspaces/beam/frappe-bench/apps/frappe" ]]
then
    echo "Bench already exists, skipping init"
    exit 0
fi

rm -rf /workspaces/beam/.git

# install node
source /home/frappe/.nvm/nvm.sh
nvm install 20
nvm alias default 20
nvm use 20
echo "nvm use 20" >> ~/.bashrc

# install yarn
npm install --global yarn

cd /workspace
bench init --frappe-branch version-15 --ignore-exist --skip-redis-config-generation frappe-bench

cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis-cache:6379
bench set-redis-queue-host redis-queue:6379
bench set-redis-socketio-host redis-socketio:6379

# Remove redis from Procfile
sed -i '/redis/d' ./Procfile

bench new-site dev.localhost --mariadb-root-password 123 --admin-password admin --no-mariadb-socket

bench get-app erpnext --branch version-15
bench get-app hrms --branch version-15
bench get-app https://github.com/agritheory/beam --branch $branch_name

bench --site dev.localhost install-app erpnext hrms beam
bench --site dev.localhost set-config developer_mode 1
bench --site dev.localhost clear-cache
bench use dev.localhost

bench build && bench clear-cache
