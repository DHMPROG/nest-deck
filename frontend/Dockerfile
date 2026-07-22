# --- build ---------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# The client talks to a relative /api, which nginx proxies — so no server IP
# is baked into the bundle and the image works on any network.
ARG VITE_API_BASE=""
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

# --- serve ---------------------------------------------------------------
FROM nginx:alpine

# Copied as a template: the base image's entrypoint runs envsubst over
# /etc/nginx/templates/*.template before starting nginx, filling in BACKEND_URL.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/build /usr/share/nginx/html

# Where to reach the backend. Override to http://host.docker.internal:8000
# when the backend runs natively (so keyboard macros and launchers work).
ENV BACKEND_URL=http://backend:8000

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
