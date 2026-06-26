# ── Frontend — nginx static server ───────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy static files
COPY login.html  /usr/share/nginx/html/login.html
COPY index.html  /usr/share/nginx/html/index.html
COPY app.js      /usr/share/nginx/html/app.js
COPY style.css   /usr/share/nginx/html/style.css

# nginx config (with env-var proxy_pass substituted at startup)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# BACKEND_URL must be set at runtime, e.g.
#   --env BACKEND_URL=https://backend-xxxx-uc.a.run.app
ENV BACKEND_URL=http://localhost:8080

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
