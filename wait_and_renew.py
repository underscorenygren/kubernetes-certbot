#!/usr/bin/env python
import datetime
import time

import util
from update_elb import Aws
from certbot import Certbot

logger = util.configure_logger()
FILENAME = './cert.lock'
SLEEP_TIME = 600


def parse_domains():

	domain = util.setting("DOMAIN")
	subdomain = util.setting("SUBDOMAIN")
	no_subdomain = util.option("NO_SUBDOMAIN")
	one_offs = util.option("ONE_OFFS")
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

	joined = ",".join(domains)
	if one_offs:
		logger.debug("adding one offs to domains: {}".format(one_offs))
		joined += ",{}".format(one_offs)

	return joined


if __name__ == "__main__":

	cert_name = util.leading_domain()
	logger.info("starting wait and renew for {} at {}".format(cert_name, str(datetime.datetime.now())))
	certbot = Certbot(cert_name, staging=util.option("STAGING"))
	aws = Aws()
	logger.debug("initialized certbot and aws")

	if util.option("RELOAD"):
		err = certbot.load()
		if err:
			logger.info("couldn't load from secret, recreating: {}".format(err))

	if not certbot.has_certificate():
		certbot.create(parse_domains())
		aws.update_cert(certbot)
	else:
		certbot.renew()

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
			certbot.renew()
			logger.debug("certs renewed, locking")
			f = open(FILENAME, 'w')
			f.write(str(datetime.datetime.now()))
			f.close()
			logger.debug("locked")
