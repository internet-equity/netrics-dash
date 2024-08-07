ARG BASE_TAG=latest

FROM chicagocdac/ndt-server:${BASE_TAG}

RUN apk add --no-cache \
    openssl            \
    python3

COPY bootstrap.py /ndt-bootstrap

RUN chmod 744 /ndt-bootstrap

ENTRYPOINT ["/ndt-bootstrap"]
