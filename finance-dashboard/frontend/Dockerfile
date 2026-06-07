# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY public/ public/
COPY src/ src/

RUN npm run build

# Runtime stage
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
