# Printers

Printers service containerized.
Caddy (with TLS) + CUPS.

<details><summary>Podman</summary>

## Initial Setup

```sh
echo 'unqualified-search-registries = ["docker.io"]' | sudo tee -a /etc/containers/registries.conf
cp .env.example .env
podman-compose build
```

## Run the container containers

### Develop

1) Ensure the `CONTAINER_TARGET` env variable is `localhost`.
2) Run the container:
```sh
podman-compose up --remove-orphans --abort-on-container-exit
```

### Production

1) Ensure the `CONTAINER_TARGET` env variable is `production`.
2) Complete the `CERTBOT_EMAIL` and `CERTBOT_DOMAIN` env variables.
3) Run the container in background:
```sh
podman-compose up --remove-orphans -d
```

## Handle containers

Stop the containers:
```sh
prefix="$(grep -E '^CONTAINER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
   podman ps --format="{{.Names}}" | grep "$prefix" | xargs -r podman kill
```

Delete everything related to containers (requires them to be stopped):
```sh
prefix="$(grep -E '^CONTAINER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
  && # Delete containers:
     podman ps -a --format="{{.Names}}" | grep "$prefix" | xargs -r podman rm \
  && # Delete volumes:
     podman volume ls --format="{{.Name}}" | grep "$prefix" | xargs -r podman volume rm \
  && # Delete bind mounts:
     awk '/volumes:/ { while (getline > 0) { if ($1 ~ /^-/) { split($2, parts, ":"); if (parts[1] ~ /^\.\//) { print parts[1] } } else { break } } }' podman-compose.yml \
     | xargs -I {} sudo rm -rf {} \
  && # Delete networks:
     podman network ls --format="{{.Name}}" | grep "$prefix" | xargs -r podman network rm
```

</details>

<details><summary>Docker</summary>

## Initial Setup

```sh
cp .env.example .env
docker compose build
```

## Run the container containers

### Develop

1) Ensure the `CONTAINER_TARGET` env variable is `localhost`.
2) Run the container:
```sh
docker compose up --remove-orphans --abort-on-container-exit
```

### Production

1) Ensure the `CONTAINER_TARGET` env variable is `production`.
2) Complete the `CERTBOT_EMAIL` and `CERTBOT_DOMAIN` env variables.
3) Run the container in background:
```sh
docker compose up --remove-orphans -d
```

## Handle containers

Stop the containers:
```sh
prefix="$(grep -E '^CONTAINER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
   docker ps --format="{{.Names}}" | grep "$prefix" | xargs -r docker kill
```

Delete everything related to containers (requires them to be stopped):
```sh
prefix="$(grep -E '^CONTAINER_NAME_PREFIX=' .env | cut -d '=' -f2)" \
  && # Delete containers:
     docker ps -a --format="{{.Names}}" | grep "$prefix" | xargs -r docker rm \
  && # Delete volumes:
     docker volume ls --format="{{.Name}}" | grep "$prefix" | xargs -r docker volume rm \
  && # Delete bind mounts:
     awk '/volumes:/ { while (getline > 0) { if ($1 ~ /^-/) { split($2, parts, ":"); if (parts[1] ~ /^\.\//) { print parts[1] } } else { break } } }' docker-compose.yml \
     | xargs -I {} sudo rm -rf {} \
  && # Delete networks:
     docker network ls --format="{{.Name}}" | grep "$prefix" | xargs -r docker network rm
```

</details>
