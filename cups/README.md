# Printers

Printers service containerized.
Caddy (with TLS) + CUPS.

## Initial Setup

```sh
cp .env.example .env
docker network create "$(grep -E '^DOCKER_NAME_PREFIX=' .env | cut -d '=' -f2)"_"$(grep -E '^DOCKER_NETWORK_NAME=' .env | cut -d '=' -f2)"
docker compose build
```

## Run container

Develop
```sh
docker compose up --remove-orphans --abort-on-container-exit
```

Production:
```sh
docker compose up --remove-orphans -d
```
