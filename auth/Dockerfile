ARG KEYCLOAK_VERSION=26.0.1

FROM quay.io/keycloak/keycloak:${KEYCLOAK_VERSION} AS base

FROM base AS dev

CMD ["start-dev", "--import-realm"]

FROM base AS prod

CMD ["start"]