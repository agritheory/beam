# Printers

Printers service containerized.
Caddy (with TLS) + CUPS.

## Initial Setup

```
cp .env.example .env
docker network create "$(grep -E '^DOCKER_NETWORK_NAME=' .env | cut -d '=' -f2)"
docker compose build
```

- Edit `caddyfile` replacing `custom-domain.com` with your real domain.

## Run container
```
docker compose up --remove-orphans --abort-on-container-exit
```
