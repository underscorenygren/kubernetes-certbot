#!/usr/bin/env python
import datetime
import logging
import os
import subprocess
import time

logger = logging.getLogger('certbot')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

logger.info("starting wait and renew at {}".format(str(datetime.datetime.now())))
FILENAME = './cert.lock'
SLEEP_TIME = 600


def env(name, ensure=True):
	val = os.environ.get(name)
	if not val and ensure:
		raise ValueError("Couldn't find {} in environment".format(name))
	return val


def parse_domains():

	domain = env("DOMAIN")
	subdomain = env("SUBDOMAIN")
	no_subdomain = env("NO_SUBDOMAIN", ensure=False)
	domains = [d.strip() for d in domain.split(',')]
	subdomains = [d.strip() for d in subdomain.split(',')]

	logger.debug("parsed main domains {}".format(domains))
	prefixed = ["{}.{}".format(_subdom, _dom) for _dom in domains for _subdom in subdomains]
	if no_subdomain:
		logger.debug("including root domains")
		domains = domains + prefixed
	else:
		logger.debug("setting only subdomains")
		domains = prefixed

	return ",".join(domains)


while True:
	logger.debug("checking lock")
	try:
		f = open(FILENAME, 'r')
		f.read()
		logger.info("Cert is locked, sleeping {}".format(SLEEP_TIME))
		f.close()
		time.sleep(SLEEP_TIME)
	except IOError:
		logger.info("no lock file, renewing certs")
		domains = parse_domains()
		subprocess.check_call(['./run.sh', domains])
		logger.debug("certs renewed, locking")
		f = open(FILENAME, 'w')
		f.write(str(datetime.datetime.now()))
		f.close()
		logger.debug("locked")
