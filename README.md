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
bench init --frappe-branch version-15 {{ bench name }} --python python3
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
```

For a complete database reset to re-run tests, run the following
```shell
bench reinstall --yes --admin-password admin --mariadb-root-password admin && bench execute 'beam.tests.setup.before_test'
```

To run backend tests

```shell
source env/bin/activate
pytest ./apps/beam/beam/tests --ignore=./apps/beam/beam/tests/mobile/ --disable-warnings -s --tracing=retain-on-failure
```

To run frontend tests

Start bench in a separate terminal, then run:

```shell
source env/bin/activate
pytest ./apps/beam/beam/tests/mobile --browser chromium --disable-warnings
```

### BEAM Portal setup

<details>
<summary>Development</summary>

```shell
# start the development server
yarn dev
```
</details>

<details>
<summary>Production</summary>

```shell
# build assets for the portal page(s)
bench build

# visit `{server URL}/beam` to access the portal page.
```
</details>

CUPS integration tests (`test_printer_cups_integration.py`) use the CUPS service container from the pytest workflow (built from [`cups/cups/Containerfile`](./cups/cups/Containerfile)). Locally, publish beam-cups (e.g. `-p 1631:631`, matching CI) and set both `BEAM_CUPS_HOST` and `BEAM_CUPS_PORT`. Without those env vars the tests skip — they must not target system cupsd on `:631` (that hangs).

### Running tests

From `apps/beam` with the bench virtualenv active:

```shell
# Full suite (unit story, then portal/Playwright at order 300+)
python -m playwright install chromium   # once per env
pytest beam/tests --browser chromium

# Unit-only
pytest beam/tests --ignore-glob='**/test_beam_*.py'
```

Portal tests (`test_beam_*.py`) start `bench serve` if needed and map the site hostname to `127.0.0.1` for Chromium (same approach as approvals). CI runs one pytest job from the Run Tests step in `.github/workflows/pytest.yaml`.

### Printer Server setup
```shell
sudo apt-get install gcc cups python3-dev libcups2-dev -y
# for development it helps to have the CUPS PDF printer installed
# sudo apt-get -y install printer-driver-cups-pdf

bench pip install pycups
sudo usermod -a -G lpadmin {username} # the "frappe" user in most installations
```

Go to `{server URL or localhost}:631` to access the CUPS web interface. Configuration on a remote server will take [extra steps](https://askubuntu.com/questions/23936/how-do-you-administer-cups-remotely-using-the-web-interface) to secure.

#### License

MIT
