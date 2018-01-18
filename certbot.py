import json
import logging
import os

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
		self.email = util.setting("LETSENCRYPT_EMAIL")

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
			rendered = pystache.render(template, {
				"name": self.secret_name,
				"namespace": self.secret_namespace,
				"chain": util.encode(chain),
				"key": util.encode(key)})
			return util.run(['kubectl', 'apply', '-f', rendered], sensitive_args=True)

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
			args = ['--non-interactive', '--agree-tos',
					'--standalone', '--standalone-supported-challenges',
					'http-01', '--email', self.emails,
					domains_string]
			self.run_certbot(args)

	def renew(self):
		if self.is_dummy():
			self.load_dummy_certs()
			update_elb.Aws().update_elb(self)
		else:
			self.run_certbot(['renew', '--deploy-hook "python update_elb.py renew"'])

	def run_cerbot(self, args):
		if 'certbot' != args[0]:
			args = ['certbot'] + args

		if self.staging and '--staging' not in args:
			args.append('--staging')

	def _path(self, _file=None):
		args = [self.cert_name, _file] if _file else [self.cert_name]
		return os.path.join("/etc/letsencrypt/live/", *args)
