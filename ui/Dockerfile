# ============================================================
# CEBD 1261 — Session 08 | ui/Dockerfile
#
# WHY THIS EXISTS:
#   In Session 07 (local), chat.html was mounted as a volume:
#     volumes:
#       - ./ui/chat.html:/usr/share/nginx/html/chat.html:ro
#
#   ACI Container Groups do NOT support volume mounts from
#   the host filesystem. The file must be baked into the image.
#
# This Dockerfile copies chat.html and nginx.conf directly
# into the nginx image at build time.
# ============================================================

FROM nginx:alpine

# Copy the chat UI into the nginx serving directory
COPY chat.html /usr/share/nginx/html/chat.html

# Copy nginx reverse-proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]