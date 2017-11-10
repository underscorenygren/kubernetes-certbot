FROM python:2.7.13-alpine
MAINTAINER Erik Nygren <sten.erik.nygren@gmail.com>

RUN apk add --no-cache --update jq dcron bash curl wget vim certbot ca-certificates && \
    wget https://storage.googleapis.com/kubernetes-release/release/v1.8.0/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

RUN pip install awscli
WORKDIR /opt/certbot

ENV DOMAIN ""
ENV SUBDOMAIN ""
ENV NO_SUBDOMAIN ""
ENV LETS_ENCRYPT_EMAIL ""
ENV AWS_ACCESS_KEY_ID ""
ENV AWS_SECRET_ACCESS_KEY ""
ENV AWS_DEFAULT_REGION ""

ADD ./wait_and_renew.py .
ADD ./crontab.file .
ADD ./run.sh .
ADD ./update_aws_cert.sh .

RUN crontab crontab.file

EXPOSE 80
CMD ["./wait_and_renew.py"]
