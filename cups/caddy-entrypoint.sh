# certbot certonly --agree-tos --domain ... --email ... -n --expand -v --standalone --dry-run
certbot certonly --standalone -d ... --email ... --agree-tos

while [ ! -f /certs/fullchain.pem ] || [ ! -f /certs/privkey.pem ]; do
    echo "Esperando a que se generen los certificados..."
    sleep 5
done

# Inicia Caddy con los certificados generados
# caddy run --config /etc/caddy/Caddyfile
