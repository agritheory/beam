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
bench get-app erpnext --branch version-14
```
Download this application and install all apps
```
bench get-app beam git@github.com:agritheory/beam.git
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

To run mypy and pytest
```shell
source env/bin/activate
mypy ./apps/beam/beam --ignore-missing-imports
pytest ./apps/beam/beam/tests -s --disable-warnings
```

### Printer Server setup
```shell
sudo apt-get install gcc cups python3-dev libcups2-dev -y
# for development it helps to have the CUPS PDF printer installed
# sudo apt-get -y install printer-driver-cups-pdf

bench pip install pycups
sudo usermod -a -G lpadmin {username} # the "frappe" user in most installations
```
Go to `{server URL or localhost}:631` to access the CUPS web interface
Configuration on a remote server will take extra steps to secure:
https://askubuntu.com/questions/23936/how-do-you-administer-cups-remotely-using-the-web-interface
