certbot renew
./caddy-entrypoint.sh
cp /etc/letsencrypt/live/tudominio.com/fullchain.pem /certs/fullchain.pem
cp /etc/letsencrypt/live/tudominio.com/privkey.pem /certs/privkey.pem
sleep infinity