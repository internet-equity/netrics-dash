# syntax=docker/dockerfile:1
FROM python:3.9-alpine3.17
# Starting with 3.14 features sqlite3.35 and "returning" clause

# Builds intended for deployment should specify the software
# version via "APPVERSION".
ARG APPVERSION
ARG APPNAME=dashboard
ARG FATEVERSION=0.1.0rc2

# Label "version" may be incremented upon changing this file.
LABEL version="3"                \
      appname="$APPNAME"         \
      appversion="$APPVERSION"   \
      fateversion="$FATEVERSION"

# Configure core app environment.
ENV APP_NAME="$APPNAME"                               \
    APP_VERSION="$APPVERSION"                         \
    APP_HOST="0.0.0.0"                                \
    APP_DATABASE="file:/var/lib/$APPNAME/data.sqlite" \
    PYTHONPATH=/usr/src/"$APPNAME"/srv                \
    PYTHONUNBUFFERED=1

# Create core app user, group and directories.
RUN <<-EOF
    set -ex

    addgroup -S "$APPNAME"
    adduser --no-create-home --disabled-password "$APPNAME" --ingroup "$APPNAME"

    mkdir -p /usr/src/"$APPNAME"
    chown "$APPNAME" /usr/src/"$APPNAME"
    chmod ug+rwx /usr/src/"$APPNAME"

    mkdir -p /var/lib/"$APPNAME"
    chown "$APPNAME" /var/lib/"$APPNAME"
    chmod ug+rwx /var/lib/"$APPNAME"
EOF

WORKDIR /usr/src/"$APPNAME"

# Copy in API source from host disk.
COPY --chown="$APPNAME":"$APPNAME" src/srv/ srv/

# ...and requirement file(s)
COPY --chown="$APPNAME":"$APPNAME" requirement/ requirement/

# Install web app (globally)
RUN set -ex \
    ; python -m pip install --no-cache-dir -r requirement/main.txt

# ...and Fate (isolated with global links)
#
# (fate installed into venv but override prefix inference to treat as system-global)
#
ENV FATE_PREFIX_PROFILE="system"

COPY etc/fate /etc/fate

RUN <<-EOF
    set -ex

    python -m venv /usr/local/lib/fate

    /usr/local/lib/fate/bin/pip install --no-cache-dir fate-scheduler=="$FATEVERSION"

    # (note: busybox ln doesn't appear to support -t as expected)
    ln -s /usr/local/lib/fate/bin/fate* /usr/local/bin
EOF

USER "$APPNAME"

WORKDIR /usr/src/"$APPNAME"/srv

CMD ["python", "-m", "app"]

EXPOSE 8080
