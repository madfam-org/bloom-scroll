# Bloom Scroll Frontend - Flutter Web Dockerfile
# Build stage
FROM ghcr.io/cirruslabs/flutter:3.24.0 AS builder

WORKDIR /app

# Copy pubspec (lockfile is generated at build time; keeping it out of VCS
# avoids churn across platforms and avoids a hard COPY failure when absent).
COPY pubspec.yaml ./

# Resolve and get dependencies
RUN flutter pub get

# Copy source code
COPY . .

# Build for web
RUN flutter build web --release

# Production stage - serve with nginx
FROM nginx:alpine AS runner

# Copy built web files
COPY --from=builder /app/build/web /usr/share/nginx/html

# Copy nginx config
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    gzip on; \
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml; \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
