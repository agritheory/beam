## BEAM

Barcode Scanning for ERPNext

#### License

MIT

## Install Instructions

Set up a new bench, substitute a path to the python version to use, which should 3.10 latest

```
# for linux development
bench init --frappe-branch version-14 {{ bench name }} --python ~/.pyenv/versions/3.10.4/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext app, its prerequisite Payments, and the HR module
```
bench get-app payments
bench get-app erpnext --branch version-14
```
Download this application and install all apps
```
bench get-app beam git@github.com:agritheory/beam.git
bench install-app erpnext approvals
```
Set developer mode in `site_config.json`
```
cd {{ site name }}
nano site_config.json

 "developer_mode": 1,
```

Update and get the site ready
```
bench start
```
In a new terminal window
```
bench update
bench migrate
bench build
```

Setup test data
```shell
bench execute 'beam.tests.setup.before_test'
# for complete reset to run before tests:
bench reinstall --yes --admin-password admin --mariadb-root-password admin && bench execute 'beam.tests.setup.before_test'
```

To run mypy
```shell
source env/bin/activate
mypy ./apps/beam/beam --ignore-missing-imports
```
