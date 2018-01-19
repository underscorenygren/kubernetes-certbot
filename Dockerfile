FROM certbot
MAINTAINER Erik Nygren <sten.erik.nygren@gmail.com>

RUN apk add --no-cache --update jq dcron bash curl wget vim ca-certificates && \
    wget https://storage.googleapis.com/kubernetes-release/release/v1.8.0/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

ADD requirements.txt .
RUN pip install -r requirements.txt

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

ADD ./dummy-*.pem ./
ADD ./secret-template.yaml ./
ADD renew.sh ./
ADD ./crontab.file .
RUN crontab crontab.file

ADD ./*.py ./

ENTRYPOINT ["python"]
CMD ["./wait_and_renew.py"]
