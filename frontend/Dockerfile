# Stage 1: Build the React 19.2.6 + React-Bootstrap 2.10.10 application
FROM node:22-alpine AS build

WORKDIR /app/frontend

COPY package.json package-lock.json ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build

# Stage 2: Serve static assets with Nginx and proxy /api & /artifacts to backend
FROM nginx:1.27-alpine

COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
