FROM debian:testing-slim

# Install Packages (basic tools, cups, basic drivers, HP drivers)
RUN apt-get update \
    && apt-get install -y \
        sudo \
        whois \
        usbutils \
        cups \
        cups-client \
        cups-bsd \
        cups-filters \
        foomatic-db-compressed-ppds \
        printer-driver-all \
        openprinting-ppds \
        hpijs-ppds \
        hp-ppd \
        hplip \
        smbclient \
        printer-driver-cups-pdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG CUPS_ADMIN_USER
ARG CUPS_ADMIN_PASSWORD
RUN useradd \
        --create-home \
        --groups sudo,lp,lpadmin \
        --shell=/bin/bash \
        --password=$(mkpasswd $CUPS_ADMIN_PASSWORD) \
        $CUPS_ADMIN_USER \
    && echo "$CUPS_ADMIN_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER $CUPS_ADMIN_USER

COPY --chown=root:lp cupsd.conf /etc/cups/cupsd.conf

CMD [\
    "/usr/sbin/cupsd", \
    "-f" \
]
