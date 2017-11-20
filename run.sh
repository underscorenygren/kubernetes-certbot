#!/bin/bash

set -eu

DOMAINS="$1"

echo "running certbot on domains $DOMAINS"

readonly SECRET_NAME=letsencrypt-cert
readonly DOMAIN_MAIN=$(echo $DOMAINS | sed 's/,.*//')
readonly SECRET_NAMESPACE=${SECRET_NAMESPACE:-default}
readonly STAGING=${STAGING:-}

if [ -z "$STAGING" ]; then
  echo "requesting live cert"
else
  echo "requesting staging cert"
fi

if [ -z "$CERT_PREFIX" ]; then
  echo "no cert name set, can't upload"
fi

echo "Generating certificate for ${DOMAIN_MAIN} (with domains $DOMAINS)"
certbot \
  --non-interactive \
  --agree-tos \
  --standalone \
  --standalone-supported-challenges http-01 \
  --email "${LETS_ENCRYPT_EMAIL}" \
  --domains "${DOMAINS}" \
  ${STAGING:+"--staging"} \
  certonly

echo "Generating kubernetes secret ${SECRET_NAME} (namespace ${SECRET_NAMESPACE})"

kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: "${SECRET_NAME}"
  namespace: "${SECRET_NAMESPACE}"
type: kubernetes.io/tls
data:
  tls.crt: "$(cat /etc/letsencrypt/live/${DOMAIN_MAIN}/fullchain.pem | base64 | tr -d '\n')"
  tls.key: "$(cat /etc/letsencrypt/live/${DOMAIN_MAIN}/privkey.pem | base64 | tr -d '\n')"
EOF

./update_aws_cert.sh $DOMAIN_MAIN

echo "completed run"
