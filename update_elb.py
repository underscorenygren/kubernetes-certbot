import time

import boto3
import botocore

import util
from certbot import Certbot

logger = util.get_logger()

class Aws(object):

	def __init__(self):

		util.setting("AWS_ACCESS_KEY_ID")
		util.setting("AWS_SECRET_ACCESS_KEY")
		iam_region = util.option("AWS_IAM_REGION", 'us-east-1')
		self.elb = boto3.client('elb')
		self.iam = boto3.client('iam', region_name=iam_region)
		self.sleep_time = 1

	def upload_cert(self, name, chain, key):
		logger.info("uploading new cert {}".format(name))
		resp = self.iam.upload_server_certificate(
				ServerCertificateName=name,
				CertificateBody=chain,
				PrivateKey=key)
		return resp['ServerCertificateMetadata']['Arn']

	def load_balancer_exists(self, name):
		try:
			self.elb.describe_load_balancer_attributes(LoadBalancerName=name)
			return True
		except botocore.exceptions.ClientError as e:
			util.ensure_typed_aws_error(e, 'AccessPointNotFound')
			return False

	def update_elb_cert(self, elb_name, arn):
		logger.info("updating ELB {} with {}".format(elb_name, arn))
		while True:
			try:
				self.elb.set_load_balancer_listener_ssl_certificate(
						LoadBalancerName=elb_name,
						LoadBalancerPort=443,
						SSLCertificateId=arn)
				break
			except botocore.exceptions.ClientError as e:
				util.ensure_typed_aws_error(e, 'CertificateNotFound')
				logger.debug("cert not present, waiting")
				time.sleep(self.sleep_time)

	def remove_cert(self, name):
		logger.info("removing cert {}".format(name))
		self.iam.delete_server_certificate(ServerCertificateName=name)

	def wait_for_cert(self, name):
		self._wait_for_cert(name, expect_missing=False)

	def wait_for_cert_missing(self, name):
		self._wait_for_cert(name, expect_missing=True)

	def has_cert(self, name):
		try:
			self.iam.get_server_certificate(ServerCertificateName=name)
			return True
		except botocore.exceptions.ClientError as e:
			util.ensure_typed_aws_error(e, 'NoSuchEntity')
			return False

	def _wait_for_cert(self, name, expect_missing=False):
		logger.info("waiting on cert {} to be {}".format(name, "missing" if expect_missing else "present"))
		while True:
			if self.has_cert(name):
				if not expect_missing:
					break
				else:
					logger.debug("cert found, waiting")
					time.sleep(self.sleep_time)
			else:
				if expect_missing:
					break
				else:
					logger.debug("cert mising, waiting")
					time.sleep(self.sleep_time)
		logger.info("finished waiting")

	def do_full_update(self, elb_name, cert_name, chain, key):
		"""AWS doesn't allow updates in place, so we do a tmp swap"""
		tmp_name = "{}-tmp".format(cert_name)
		try:
			if self.has_cert(tmp_name):
				self.remove_cert(tmp_name)
		except botocore.exceptions.ClientError as e:
			util.ensure_typed_aws_error(e, 'DeleteConflict')
			logger.info("couldn't remove tmp cert")
		self.wait_for_cert_missing(tmp_name)

		try:
			arn = self.upload_cert(tmp_name, chain, key)
			self.wait_for_cert(tmp_name)
			self.update_elb_cert(elb_name, arn)

		except botocore.exceptions.ClientError as e:
			util.ensure_typed_aws_error(e, 'DeleteConflict')
			logger.info("couldn't delete old cert, must be set from different deploy. Continuing")

		while True:
			try:
				self.remove_cert(cert_name)
				self.wait_for_cert_missing(cert_name)
				break
			except botocore.exceptions.ClientError as e:
				util.ensure_typed_aws_error(e, 'DeleteConflict')
				logger.info("couldn't delete main cert, sleeping and retrying")
				time.sleep(1)

		arn = self.upload_cert(cert_name, chain, key)
		logger.info("uploaded cert {} as {}".format(cert_name, arn))
		self.wait_for_cert(cert_name)
		logger.info("sleeping arbitrarily to make cert resolve")
		time.sleep(20)
		self.update_elb_cert(elb_name, arn)
		while True:
			try:
				if self.has_cert(tmp_name):
					self.remove_cert(tmp_name)
				break
			except botocore.exceptions.ClientError as e:
				util.ensure_typed_aws_error(e, 'DeleteConflict')
				logger.info("couldn't delete tmp cert, must be set from different deploy. Continuing")

	def update_cert(self, certbot):
		elb_name = util.setting("ELB_NAME")
		ssl_name = "{}-letsencrypt".format(util.setting("CERT_PREFIX"))
		cert_name = certbot.cert_name
		if not certbot.has_certificate():
			logger.error("cannot update elb for cert name({}), not present on disk".format(cert_name))
		elif not self.load_balancer_exists(elb_name):
			logger.error("Load balancer {} does not exist".format(elb_name))
		else:
			data = certbot.chain_data()
			key = certbot.key_data()
			self.do_full_update(elb_name, ssl_name, data, key)
			certbot.update_secret(data, key)

	def renew(self):
		certbot = Certbot(util.parse_domains().split(",")[0])
		self.update_cert(certbot)


if __name__ == "__main__":

	import argparse
	parser = argparse.ArgumentParser(help="does ELB stuff")
	parser.add_argument('fn_name', type=str, help="name of fn to call")
	parser.add_argument('-a', '--args', nargs="*", required=False)
	parser.add_argument('-kw', '--kwarg', action='append', type=str, required=False)

	args = parser.parse_args()
	logger = util.configure_logger()
	aws = Aws()
	fn = getattr(aws, args.fn_name)
	kwargs = dict([entry.split("=") for entry in args.kwarg])
	fn(*args, **kwargs)
