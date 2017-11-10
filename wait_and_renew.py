#!/usr/bin/env python
import datetime
import subprocess
import time

print "starting wait and renew"
FILENAME = './cert.lock'
SLEEP_TIME = 600

while True:
	try:
		open(FILENAME, 'r').read()
		print "Cert is locked, sleeping"
		time.sleep(SLEEP_TIME)
	except IOError:
		print "no lock file, renewing certs"
		subprocess.check_call('./run.sh')
		print "renewed, locking"
		f = open(FILENAME, 'w')
		f.write(str(datetime.datetime.now()))
		f.close()
