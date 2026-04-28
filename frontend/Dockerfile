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

# API base URL is read at compile time via `String.fromEnvironment(...)` in
# `lib/services/api_config.dart`. The Dart compiler bakes the value into the
# JS bundle at `flutter build` — there's no runtime env var path. Default to
# production; override with `--build-arg API_BASE_URL=http://localhost:8000`
# for local dev builds.
#
# Why hardcode the prod default: the enclii reusable build workflow
# (madfam-org/enclii/.github/workflows/build-publish.yml) doesn't currently
# expose a `build_args` input to consumer repos. Embedding the prod URL
# here is the smallest correct fix to unbreak production. Same class of bug
# as the `feedback_nextjs_build_args.md` memory entry (Next.js NEXT_PUBLIC_*)
# and the bit-rondelio + karafiel build-arg fixes earlier this quarter.
ARG API_BASE_URL=https://api.almanac.solar

# Build for web. `--dart-define=K=V` threads compile-time constants into
# `String.fromEnvironment(K)`.
RUN flutter build web --release --dart-define=API_BASE_URL=${API_BASE_URL}

# Production stage - serve with nginx
FROM nginx:alpine AS runner

# Copy built web files
COPY --from=builder /app/build/web /usr/share/nginx/html

# Custom nginx config:
# - listen on 8080 (any non-privileged port; K8s runs as uid 1001 and
#   can't bind <1024)
# - PID file + all cache/temp dirs go to /tmp so the non-root user
#   can write (default /var/cache/nginx is root-owned)
RUN rm /etc/nginx/conf.d/default.conf && \
    printf 'pid /tmp/nginx.pid;\n\
worker_processes auto;\n\
error_log /dev/stderr warn;\n\
events { worker_connections 1024; }\n\
http {\n\
    include /etc/nginx/mime.types;\n\
    default_type application/octet-stream;\n\
    access_log /dev/stdout;\n\
    client_body_temp_path /tmp/client_body;\n\
    proxy_temp_path /tmp/proxy;\n\
    fastcgi_temp_path /tmp/fastcgi;\n\
    uwsgi_temp_path /tmp/uwsgi;\n\
    scgi_temp_path /tmp/scgi;\n\
    sendfile on;\n\
    keepalive_timeout 65;\n\
    gzip on;\n\
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;\n\
    server {\n\
        listen 8080;\n\
        server_name _;\n\
        root /usr/share/nginx/html;\n\
        index index.html;\n\
        location / { try_files $uri $uri/ /index.html; }\n\
    }\n\
}\n' > /etc/nginx/nginx.conf && \
    chown -R 1001:1001 /usr/share/nginx/html /var/log/nginx /var/cache/nginx /etc/nginx && \
    # nginx:alpine's /docker-entrypoint.d scripts try to mkdir
    # /var/cache/nginx/client_temp even when the main config overrides the
    # temp paths. Pre-create the subdirs uid 1001 can write to so the
    # entrypoint succeeds before the main config takes over.
    mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R 1001:1001 /var/cache/nginx

# Run as the non-root user (k8s SecurityContext already enforces this,
# but set USER too so local `docker run` behaves the same).
USER 1001

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
