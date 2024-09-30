<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

## BEAM

Barcode Scanning for ERPNext

## Codespace

To run this project in a Github Codespace, click on the button below.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/agritheory/beam?quickstart=1)

After the codespace is ready, you can run the following command in the terminal to start the Frappe server:

```shell
bench start
```

You can also build the project by running the following commands in the terminal:

```shell
cd apps/beam
yarn install
bench build --app beam && bench clear-cache
```

If you're trying to review a pull request inside the codespace, you can follow the instructions in the [official guide](https://docs.github.com/en/codespaces/developing-in-a-codespace/using-github-codespaces-for-pull-requests#reviewing-a-pull-request-in-codespaces).

## Install Instructions

Set up a new bench, substitute a path to the python version to use, which should be 3.10 latest

```
# for linux development
bench init --frappe-branch version-15 {{ bench name }} --python ~/.pyenv/versions/3.10.13/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext app
```
bench get-app erpnext --branch version-15
```
Download this application and install all apps
```
bench get-app beam --branch version-15 git@github.com:agritheory/beam.git
```
Set developer mode in `site_config.json`
```
cd {{ site name }}
nano site_config.json

 "developer_mode": 1,
```
Enable server scripts
```
bench set-config -g server_script_enabled 1
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

#### License

MIT
