#!/usr/bin/env python
import datetime
import time

import util
from update_elb import Aws
from certbot import Certbot

logger = util.configure_logger()
FILENAME = './cert.lock'
SLEEP_TIME = 600


if __name__ == "__main__":

	domains_str = util.parse_domains()
	cert_name = domains_str.split(',')[0]
	logger.info("starting wait and renew for {} at {}".format(cert_name, str(datetime.datetime.now())))
	certbot = Certbot(cert_name, staging=util.option("STAGING"))
	aws = Aws()
	logger.debug("initialized certbot and aws")

	if util.option("RELOAD"):
		err = certbot.load()
		if err:
			logger.info("couldn't load from secret, recreating: {}".format(err))

	if not certbot.has_certificate():
		certbot.create(domains_str)
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
