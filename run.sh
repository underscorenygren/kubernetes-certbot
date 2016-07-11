#/bin/bash -e

EMAIL="${1}"
DOMAINS="${2}"
SECRET_NAMESPACE="${SECRET_NAMESPACE:-default}"
SECRET_NAME_PREFIX="${SECRET_NAME_PREFIX:-letsencrypt}"

for DOMAIN in ${DOMAINS}; do

SECRET_NAME="${SECRET_NAME_PREFIX}-${DOMAIN//[^a-z0-9]/-}"

echo "Generating certificate ${DOMAIN}"
letsencrypt-auto \
  --non-interactive \
  --agree-tos \
  --standalone \
  --standalone-supported-challenges http-01 \
  --http-01-port 80 \
  --email "${EMAIL}" \
  --domains "${DOMAIN}" \
  certonly

echo "Generating kubernetes secret ${SECRET_NAME} (namespace ${SECRET_NAMESPACE})"
(cat << EOF
apiVersion: v1
kind: Secret
metadata:
  name: "${SECRET_NAME}"
  namespace: "${SECRET_NAMESPACE}"
type: Opaque
data:
  cert.pem: "$(cat /etc/letsencrypt/live/${DOMAIN}/cert.pem | base64 --wrap=0)"
  chain.pem: "$(cat /etc/letsencrypt/live/${DOMAIN}/chain.pem | base64 --wrap=0)"
  fullchain.pem: "$(cat /etc/letsencrypt/live/${DOMAIN}/fullchain.pem | base64 --wrap=0)"
  privkey.pem: "$(cat /etc/letsencrypt/live/${DOMAIN}/privkey.pem | base64 --wrap=0)"
EOF
) > "${SECRET_NAMESPACE}-${SECRET_NAME}.yml"
kubectl apply -f "${SECRET_NAMESPACE}-${SECRET_NAME}.yml"

done
