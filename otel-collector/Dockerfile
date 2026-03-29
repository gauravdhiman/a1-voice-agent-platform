# OTel Collector Dockerfile for Production (Render.com)
# Bakes in the config so no volume mount is needed
FROM otel/opentelemetry-collector-contrib:latest

# Copy the production config into the image
COPY otel-collector/config.production.yml /etc/otel-collector-config.yml

# Override the default command to use our config
CMD ["--config=/etc/otel-collector-config.yml"]
