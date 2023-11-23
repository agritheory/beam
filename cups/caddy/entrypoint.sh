#!/bin/sh
# set -e

# Generate and validate the certificate for the first time.
if [ ! -d /var/www/certs ] || [ -z "$(ls -A /var/www/certs)" ]; then
    mkdir /var/www/certs
    mkdir -p /var/www/html/.well-known/acme-challenge

    caddy run --config /etc/caddy/Caddyfile.not_ssl > caddy.log 2>&1 &
    echo $! > caddy.pid

    certbot certonly --webroot -w /var/www/html -d "$CERTBOT_DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos
    cp /etc/letsencrypt/live/"$CERTBOT_DOMAIN"/fullchain.pem /var/www/certs/fullchain.pem
    cp /etc/letsencrypt/live/"$CERTBOT_DOMAIN"/privkey.pem /var/www/certs/privkey.pem

    kill -SIGINT "$(cat caddy.pid)"
    rm caddy.pid
fi

# Try to renew the certificate every day.
echo "0 0 * * * certbot renew --quiet" | crontab -

caddy run --config /etc/caddy/Caddyfile.ssl
