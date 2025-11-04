# Minimal Nginx image for CloudPros Web UI
FROM nginx:1.27-alpine

# Remove default nginx configuration and html files
RUN rm -rf /etc/nginx/conf.d/* /usr/share/nginx/html/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy static web files
COPY index.html styles.css /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -q --tries=1 -O /dev/null http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
