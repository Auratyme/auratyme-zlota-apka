FROM node:23-alpine AS base

WORKDIR /app

FROM base AS dev

RUN apk add curl

COPY package.json package-lock.json ./

RUN npm i

COPY . .

CMD ["npm", "run", "start:dev"]

FROM base AS prod

COPY package.json package-lock.json ./

RUN npm ci --omit=dev

COPY . .

USER node

CMD ["npm", "run", "start:prod"]