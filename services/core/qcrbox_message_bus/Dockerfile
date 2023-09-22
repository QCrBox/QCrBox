FROM rabbitmq:3.12.5-management-alpine
SHELL ["/bin/bash", "-c"]

RUN apk add --update supervisor tmux yarn
WORKDIR /opt/app

COPY wait-for /usr/local/bin
RUN chmod a+x /usr/local/bin/wait-for

COPY ./supervisord.conf .

CMD ["supervisord"]
