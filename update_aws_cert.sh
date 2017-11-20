#!/bin/bash

if [ -z "$ELB_NAME" ]; then
  echo "no elb name set"
  exit 1
fi

if [ -z "$CERT_PREFIX" ]; then
  echo "no prefix set"
  exit 1
fi

readonly DOMAIN_MAIN=$1
CERT_NAME="$CERT_PREFIX-letsencrypt"
CERT_NAME_TMP="$CERT_NAME-tmp"
CERT_PATH=file:///etc/letsencrypt/live/${DOMAIN_MAIN}/
PRIV_KEY_PATH=$CERT_PATH/privkey.pem
BODY_PATH=$CERT_PATH/fullchain.pem
SLEEP_TIME=20

if [ -z "$DOMAIN_MAIN" ]; then
  echo "No domain name provided"
  exit 1
fi

echo "replacing cert $CERT_NAME"
TMP_ARN=$(aws iam upload-server-certificate --server-certificate-name "$CERT_NAME_TMP" --certificate-body $BODY_PATH --private-key $PRIV_KEY_PATH --region us-east-1 | jq -r .ServerCertificateMetadata.Arn)
echo "created $TMP_ARN for tmp, waiting for availability"
sleep $SLEEP_TIME
echo "finished sleep, setting cert"
aws elb set-load-balancer-listener-ssl-certificate --load-balancer-name "$ELB_NAME" --load-balancer-port 443 --ssl-certificate-id $TMP_ARN
echo "sleeping after set"
sleep $SLEEP_TIME
echo "deleting old cert $CERT_NAME"
aws iam delete-server-certificate --server-certificate-name $CERT_NAME --region us-east-1
sleep $SLEEP_TIME
echo "creating new realz cert"
ARN=$(aws iam upload-server-certificate --server-certificate-name "$CERT_NAME" --certificate-body $BODY_PATH --private-key $PRIV_KEY_PATH --region us-east-1 | jq -r .ServerCertificateMetadata.Arn)
echo "created $ARN for realz, waiting for available"
sleep $SLEEP_TIME
echo "finished sleep, setting load balancer"
aws elb set-load-balancer-listener-ssl-certificate --load-balancer-name "$ELB_NAME" --load-balancer-port 443 --ssl-certificate-id $ARN
echo "set load balancer, deleting tmp after sleep"
sleep $SLEEP_TIME
aws iam delete-server-certificate --server-certificate-name $CERT_NAME_TMP --region us-east-1
echo "done"
