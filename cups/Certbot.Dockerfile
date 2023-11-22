FROM certbot/certbot

# Directorio para almacenar los certificados
# WORKDIR /certs

# Copia el script para renovar los certificados y los archivos de configuración
# COPY ./renew-certificates.sh /certs/renew-certificates.sh
# COPY ./caddy-entrypoint.sh /certs/caddy-entrypoint.sh
# ADD ./renew-certificates.sh /certs/renew-certificates.sh
# ADD ./caddy-entrypoint.sh /certs/caddy-entrypoint.sh

# Cambia los permisos de los scripts para que sean ejecutables
# RUN chmod +x /certs/renew-certificates.sh
# RUN chmod +x /certs/caddy-entrypoint.sh

# Script para renovar automáticamente los certificados
# ENTRYPOINT "/certs/renew-certificates.sh"
WORKDIR /certs

RUN echo "sleep infinity" >> /certs/test.sh
RUN chmod +x /certs/test.sh
ENTRYPOINT "/certs/test.sh"