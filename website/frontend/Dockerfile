# Build context is website/frontend/ (see docker-compose.yml).
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite bakes VITE_* vars into the static bundle at build time, not runtime -
# they must arrive as build args, not just container env vars.
ARG VITE_RUNTIME_ORIGIN
ARG VITE_API_BASE_URL
ARG VITE_AUTH_PROVIDER
ARG VITE_AVATAR_ENGINE_MODE
ARG VITE_TRYON_ENGINE_MODE
ARG VITE_INTEGRATION_MODE
ARG VITE_ANALYTICS_ENABLED
ARG VITE_APP_VERSION
ARG VITE_APP_ENV
ENV VITE_RUNTIME_ORIGIN=$VITE_RUNTIME_ORIGIN \
    VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_AUTH_PROVIDER=$VITE_AUTH_PROVIDER \
    VITE_AVATAR_ENGINE_MODE=$VITE_AVATAR_ENGINE_MODE \
    VITE_TRYON_ENGINE_MODE=$VITE_TRYON_ENGINE_MODE \
    VITE_INTEGRATION_MODE=$VITE_INTEGRATION_MODE \
    VITE_ANALYTICS_ENABLED=$VITE_ANALYTICS_ENABLED \
    VITE_APP_VERSION=$VITE_APP_VERSION \
    VITE_APP_ENV=$VITE_APP_ENV

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
