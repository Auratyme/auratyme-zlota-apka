FROM node:22-alpine as base

WORKDIR /app

FROM base as dev

RUN apk add curl

COPY package.json package-lock.json ./

RUN npm i

COPY . .

CMD ["npm", "run", "start:dev"]

FROM base as prod

COPY package.json package-lock.json ./

RUN npm ci --omit=dev

COPY . .

USER node

CMD ["npm", "run", "start:prod"]