FROM python:2.7.13-alpine
MAINTAINER Erik Nygren <sten.erik.nygren@gmail.com>

RUN apk add --no-cache --update jq dcron bash curl wget vim certbot ca-certificates && \
    wget https://storage.googleapis.com/kubernetes-release/release/v1.8.0/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

ADD requirements.txt .
RUN pip install -r requirements.txt
WORKDIR /opt/certbot

ENV DOMAIN ""
ENV SUBDOMAIN ""
ENV NO_SUBDOMAIN ""
ENV ELB_NAME ""
ENV ONE_OFFS ""
ENV AWS_ACCESS_KEY_ID ""
ENV AWS_SECRET_ACCESS_KEY ""
ENV AWS_DEFAULT_REGION ""
ENV LETS_ENCRYPT_EMAIL ""
ENV STAGING ""
ENV SECRET_TEMPLATE ""

EXPOSE 80

ADD ./dummy-*.pem ./
ADD ./secret-template.yaml ./
ADD ./crontab.file .
RUN crontab crontab.file

ADD ./*.py ./

CMD ["./wait_and_renew.py"]
