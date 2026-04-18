# syntax=docker/dockerfile:1.6
#
# FieldPack AI — frontend image
#
# Stage 1 builds the React/Vite app into static assets.
# Stage 2 serves them through nginx on port 5173 and proxies /api + /ws to
# the backend container.

FROM node:20.19-alpine AS build

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci

COPY . ./
RUN npm run build


FROM nginx:1.29-alpine AS runtime

COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:5173/ >/dev/null 2>&1 || exit 1
