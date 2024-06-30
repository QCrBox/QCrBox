FROM nats:2.10.16-alpine

RUN apk add --update bash curl

HEALTHCHECK \
    --interval=60s \
    #--start-period=${STARTUP_TIME}s \
    #--start-interval=${STARTUP_TIME}s \
    CMD curl --fail http://127.0.0.1:8222/healthz || exit 1

SHELL ["/bin/bash", "-c"]
CMD ["nats-server", "--jetstream", "-m", "8222", "--store_dir", "/mnt/nats/", "--server_name", "qcrbox-nats"]
