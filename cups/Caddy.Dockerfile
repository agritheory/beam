FROM caddy:2.7.5-alpine

RUN apk update \
    && apk add \
        certbot

# RUN certbot certonly --agree-tos --domain ... --email ... -n --expand -v

# CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
