ARG POSTGRES_VERSION=17

FROM postgres:${POSTGRES_VERSION}-alpine

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=schedules

CMD ["postgres"]