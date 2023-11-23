# Printers

Printers service containerized.
Caddy (with TLS) + CUPS.

## Initial Setup

```sh
cp .env.example .env
docker network create "$(grep -E '^DOCKER_NAME_PREFIX=' .env | cut -d '=' -f2)"_"$(grep -E '^DOCKER_NETWORK_NAME=' .env | cut -d '=' -f2)"
docker compose build
```

## Run the container containers

### Develop

1) Ensure the `DOCKER_TARGET` env variable is `localhost`.
2) Run the container:
```sh
docker compose up --remove-orphans --abort-on-container-exit
```

### Production

1) Ensure the `DOCKER_TARGET` env variable is `production`.
2) Complete the `CERTBOT_EMAIL` and `CERTBOT_DOMAIN` env variables.
3) Run the container in background:
```sh
docker compose up --remove-orphans -d
```

## Handle containers

Stop the containers:
```sh
prefix="$(grep -E '^DOCKER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
  && docker kill $(docker ps --format="{{.Names}}" | grep "$prefix")
```

Delete everything related to containers (requires a prior STOP):
```sh
prefix="$(grep -E '^DOCKER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
  && docker rm $(docker ps -a --format="{{.Names}}" | grep "$prefix") || true \
  && docker volume rm $(docker volume ls --format="{{.Name}}" | grep "$prefix") || true \
  && docker network rm $(docker network ls --format="{{.Name}}" | grep "$prefix") || true
```
