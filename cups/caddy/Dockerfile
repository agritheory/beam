FROM caddy:2.7.5-alpine AS base

RUN apk update \
    && apk add --no-cache \
        certbot

COPY \
        Caddyfile.ssl \
        Caddyfile.not_ssl \
        Caddyfile.localhost \
    /etc/caddy/

RUN cd /etc/caddy \
    && sed -i "s/<DOMAIN>/${DOMAIN}/g" Caddyfile.* \
    && caddy fmt --overwrite

FROM base AS localhost

CMD [\
    "caddy", \
    "run", \
    "--config=/etc/caddy/Caddyfile.localhost" \
]

FROM base AS production

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT "/entrypoint.sh"
