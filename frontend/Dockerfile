# Multi-stage Dockerfile for React Vite Frontend

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve via Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 / 5174
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
