# kubernetes-certbot

Uses [certbot][certbot] to obtain an X.509 certificate from [Let's encrypt][letsencrypt] and stores it as secret in
[Kubernetes][kubernetes] for a named kubernetes cluster with an AWS load balancer entrypoint. Renews certificates
automatically.

## Usage

Settings are provided to the container via env variables and secrets. Modify `kube.yaml` to suit your needs.

- `DOMAIN`: Is the top level domain for your org, e.g. `example.com`, that is shared with all your clusters.
- `SUBDOMAIN`: Is the name of the cluster to issue a credential for, e.g. `mycluster` to issue certs for `mycluster.example.com`.
- `NO_SUBDOMAIN`: Optional setting, set to any value to expose a cluster under the root domain, e.g. to host a website under `example.com`.
  NB that subdomain must still be set, e.g. `production` as cluster with this setting on becomes `production.example.com` and `example.com`
- `ELB_NAME`: The name of your (classic) ELB to update. This is an hex value, e.g. `{some-hex-value-is-name}.us-east-1.elb.amazonaws.com`
- `STAGING`: Set to a truthy value to issue certs from letsencrypts staging environment. Start with it on - they have stringent API rate limits.
- `LETS_ENCRYPT_EMAIL` - email to associate lets encrypt with
- `aws` secret with `key`, `secret` and `region` with permission to edit ELB


## Installation

Create the service from the `service.yaml`
```
kubectl create -f service.yaml
```

Create an aws user with permission to update a classic elb. [Here is a terraform module to get you started](examples/letsencrypt.tf).

Fill in your secret in kubernetes (hot tip: prefix with a space if you don't want to store it in your bash history).

```
 kubectl create secret generic letsencrypt-aws --from-literal=key=KEY --from-literal=secret=SECRET --from-literal=region=REGION
```

Fill in the settings specified above in a config file and create it.
You can put it in `config/` (or elsewhere that suits, but that folder is .gitignored by default)
```
kubectl create configmap letsencrypt-config --from-file=./config/my-config
```

Because of some legacy deps, the subdomain is kept in a secret separately. Update kube.yaml to change
that or create that secret:

`kubectl create secret generic website --from-literal=cluster_name=mycluster`


Create the certbot pod:

```
kubectl create -f kube.yaml
```

Add routing logic to it to your entry pod running in the cluster. For Nginx:

```
...

server {
  listen 443 ssl;

  ssl_certificate /letsencrypt/tls.crt;
  ssl_certificate_key /letsencrypt/tls.key;

  ...
}

...

server {
  listen 80;

  location ^~ /.well-known/acme-challenge/ {
    proxy_pass http://certbot;
  }

  ...
}
```

Mount the secret in the `spec` part of your deployment:
```yaml
kind: Deployment
...
spec:
  template:
    spec:
      containers:
        ...
        volumeMounts:
        - name: letsencrypt
          mountPath: /letsencrypt/
          readOnly: true
      volumes:
      - name: letsencrypt
        secret:
          secretName: letsencrypt-cert
```

You can do this ahead of time by creating an empty letsencryt secret

## Implementation Details and History

This is based on the work of https://github.com/pjmorr/kubernetes-certbot, but eschews the use
of the ingress controller.

It uses a python image and entrypoint, because I prefer python scripting to bash. However,
some bash scripts are kept and edited in place.

To make renewal more straighforward, it uses a lock file to block updates,
and uses cron to remove the file to enable renewal at a set interval.

It uses the aws-cli to dynamically update the ELB when certs are issued.

My nginx setup auto-reloads, so this process doesn't handle sending a SIGHUP to Nginx
to reload the new certs.

## Future Work

Support hosting deeper subdomains, e.g. `api.cluster.example.com`

Back up letsencrypt certs on generation, to S3 most likely.

Send/signal NOHUP on renewal to allow Nginx to restart?

[letsencrypt]: https://letsencrypt.org/
[certbot]: https://github.com/certbot/certbot
[kubernetes]: http://kubernetes.io/
[nginx]: https://nginx.org/
[kubedns]: https://github.com/kubernetes/kubernetes/tree/master/build/kube-dns
