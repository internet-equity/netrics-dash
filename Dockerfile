FROM python:3.9-alpine3.14
# Starting with 3.14 features sqlite3.35 and "returning" clause

# Builds intended for deployment should specify the software
# version via "APPVERSION".
ARG APPVERSION
ARG APPNAME=dashboard

# Label "version" may be incremented upon changing this file.
LABEL version="2" \
      appname="$APPNAME" \
      appversion="$APPVERSION"

ENV APP_NAME="$APPNAME" \
    APP_VERSION="$APPVERSION" \
    APP_HOST="0.0.0.0" \
    APP_DATABASE="file:/var/lib/$APPNAME/data.sqlite" \
    PYTHONPATH=/usr/src/"$APPNAME"/srv \
    PYTHONUNBUFFERED=1

RUN set -ex && \
    addgroup -S "$APPNAME" && \
    adduser --no-create-home --disabled-password "$APPNAME" --ingroup "$APPNAME" && \
    mkdir -p /usr/src/"$APPNAME" && \
    chown "$APPNAME" /usr/src/"$APPNAME" && \
    chmod ug+rwx /usr/src/"$APPNAME" && \
    mkdir -p /var/lib/"$APPNAME" && \
    chown "$APPNAME" /var/lib/"$APPNAME" && \
    chmod ug+rwx /var/lib/"$APPNAME"

WORKDIR /usr/src/"$APPNAME"

# Copy in API source from host disk
COPY --chown="$APPNAME":"$APPNAME" src/ .

# ...and requirement file(s)
COPY --chown="$APPNAME":"$APPNAME" requirement/ requirement/

RUN set -ex && \
    python -m pip install --no-cache-dir -r requirement/main.txt

USER "$APPNAME"

WORKDIR /usr/src/"$APPNAME"/srv

CMD ["python", "-m", "app"]

EXPOSE 8080
