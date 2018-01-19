import json
import logging
import os
import subprocess
import tempfile
import time

import pystache

import update_elb
import util


logger = logging.getLogger('certbot')


class Certbot(object):

	DUMMY_SIGNAL = 'dummy'
	privkey = 'privkey.pem'
	fullchain = 'fullchain.pem'

	def __init__(self, cert_name,
			staging=False,
			secret_name='letsencrypt-cert',
			secret_namespace='default'):

		self.cert_name = cert_name
		self.staging = staging
		self.secret_name = secret_name
		self.secret_namespace = secret_namespace
		self.email = util.setting("LETS_ENCRYPT_EMAIL")
		if staging:
			logger.info("running in staging mode")

	def load(self):
		if self.is_dummy():
			self.load_dummy_certs()
			return None

		logger.info("loading certs from k8s secret {}".format(self.secret_name))

		out, err = util.run(['kubectl', 'get', 'secret', self.secret_name, '-o', 'json'])
		if err:
			return err
		loaded = json.loads(out)
		self.write_local_cert(util.decode(loaded['tls.crt']), util.decode(loaded['tls.key']))
		return None

	def write_local_cert(self, chain, key):
		os.makedirs(self._path())
		for (filename, data) in [(self.fullchain, chain),
				(self.privkey, key)]:
			logger.debug("writing local {}".format(filename))
			with open(self._path(filename), 'w') as f:
				f.write(data)
				f.flush()

	def chain_data(self):
		return self._read(self.fullchain)

	def key_data(self):
		return self._read(self.privkey)

	def _read(self, file_name):
		with open(self._path(file_name), 'r') as f:
			return f.read()

	def update_secret(self, chain, key):
		logger.info("updating k8s secret")
		template = util.option("SECRET_TEMPLATE", 'secret-template.yaml')
		if not template:
			raise ValueError("No template set")
		with open(template, 'r') as f:
			template = f.read()
			with tempfile.NamedTemporaryFile() as tf:
				rendered = pystache.render(template, {
					"name": self.secret_name,
					"namespace": self.secret_namespace,
					"chain": util.encode(chain),
					"key": util.encode(key)})
				tf.write(rendered)
				return util.run(['kubectl', 'apply', '-f', tf.name], sensitive_args=True)

	def has_certificate(self):
		return os.path.exists(self._path())

	def is_dummy(self):
		return self.staging and self.staging.lower() == self.DUMMY_SIGNAL

	def load_dummy_certs(self):
		dummy_data = []
		if self.has_certificate():
			logger.debug("skipping load, certs already present")
			return

		logger.info("loading dummy certs")
		for filename in [self.fullchain, self.privkey]:
			dummy_filepath = "./{}-{}".format(self.DUMMY_SIGNAL, filename)
			with open(dummy_filepath, 'r') as _file:
				dummy_data.append(_file.read())

		(chain, key) = dummy_data

		self.write_local_cert(chain, key)

	def create(self, domains_string):
		if self.is_dummy():
			self.load_dummy_certs()
		else:
			args = ['certonly', '--non-interactive', '--agree-tos',
					'--standalone', '--standalone-supported-challenges',
					'http-01', '--email', self.email,
					'-d', domains_string]
			if self.staging:
				args.append('--staging')
			self.run_certbot(args)

	def renew(self):
		if self.is_dummy():
			self.load_dummy_certs()
			update_elb.Aws().update_elb(self)
		else:
			self.run_certbot(['renew', '--renew-hook', "sh {}".format(os.path.join(os.path.realpath(__file__), 'renew.sh'))])

	def run_certbot(self, args):
		if 'certbot' != args[0]:
			args = ['certbot'] + args

		max_tries = 3
		worked = False
		for i in xrange(1, max_tries + 1):
			try:
				util.run(args)
				worked = True
				break
			except subprocess.CalledProcessError as e:
				if e.output.find("unknownHost") != -1:
					sleep_time = i * 10
					logger.info("catching unknown host error and sleeping {}s to try to recover".format(sleep_time))
					time.sleep(sleep_time)
				else:
					raise e
		if not worked:
			raise Exception("Too many unknown host exceptions")

	def _path(self, _file=None):
		args = [self.cert_name, _file] if _file else [self.cert_name]
		return os.path.join("/etc/letsencrypt/live/", *args)
