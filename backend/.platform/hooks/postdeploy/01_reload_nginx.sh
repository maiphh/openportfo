#!/bin/bash
set -euo pipefail
# Ensure nginx picks up https.conf + certs after deploy.
if [ -f /etc/pki/tls/certs/server.crt ] && [ -f /etc/pki/tls/private/server.key ]; then
  nginx -t
  systemctl reload nginx || systemctl restart nginx
fi
