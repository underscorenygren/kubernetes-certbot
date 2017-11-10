#!/usr/bin/env python
import datetime
import subprocess
import time
import logging

logger = logging.getLogger('certbot')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

logger.info("starting wait and renew at {}".format(str(datetime.datetime.now())))
FILENAME = './cert.lock'
SLEEP_TIME = 600

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
		subprocess.check_call('./run.sh')
		logger.debug("certs renewed, locking")
		f = open(FILENAME, 'w')
		f.write(str(datetime.datetime.now()))
		f.close()
		logger.debug("locked")
