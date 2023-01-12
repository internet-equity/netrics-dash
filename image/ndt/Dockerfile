FROM chicagocdac/ndt-server:v0.20.17

RUN apk add --no-cache \
    openssl            \
    python3

COPY bootstrap.py /ndt-bootstrap

RUN chmod 744 /ndt-bootstrap

ENTRYPOINT ["/ndt-bootstrap"]
