ARG NGINX_VERSION=1.27.1

FROM nginx:${NGINX_VERSION}-alpine AS base

FROM base as dev

RUN apk add curl

FROM base as prod