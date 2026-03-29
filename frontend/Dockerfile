FROM node:20-alpine AS build

WORKDIR /app

ENV NODE_ENV=development

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_STREAM_WS_URL=ws://localhost:8000/ws/streams
ARG VITE_ALERT_WS_URL=ws://localhost:8000/ws/alerts
ARG VITE_METRICS_WS_URL=ws://localhost:8000/ws/metrics

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_STREAM_WS_URL=$VITE_STREAM_WS_URL
ENV VITE_ALERT_WS_URL=$VITE_ALERT_WS_URL
ENV VITE_METRICS_WS_URL=$VITE_METRICS_WS_URL

COPY package.json package-lock.json ./
RUN npm ci --include=dev

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
