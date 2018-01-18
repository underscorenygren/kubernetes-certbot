import base64
import logging
import os
import subprocess


def _env(name, ensure=True, default=None):
	val = os.environ.get(name, default)
	if not val and ensure:
		raise ValueError("Missing requires setting {} in environment".format(name))
	elif not val and default:
		val = default
	try:
		val = val.strip('"').strip("'")
	except AttributeError:
		pass
	return val


def option(name, default=None):
	return _env(name, default=default, ensure=False)


def setting(name):
	return _env(name, ensure=True)


def get_logger(name='certbot'):
	return logging.getLogger('certbot')


def configure_logger(name='certbot'):
	logger = get_logger(name=name)
	logger.addHandler(logging.StreamHandler())
	logger.setLevel(logging.DEBUG if option("DEBUG") else logging.INFO)
	return logger


def leading_domain():
	return setting("DOMAIN").split(',')[0]


def encode(data):
	"""Encodes base64"""
	return base64.b64encode(data).strip("\n")


def decode(data):
	"""decodes base64"""
	return base64.b64decode(data)


def run(args, sensitive_args=False):
	"""Runs and logs a command"""
	logger = get_logger()
	cmd_str = " ".join(args)
	logged_cmd_str = cmd_str if not sensitive_args else " ".join(args[:3] + ["..."])
	try:
		logger.debug(logged_cmd_str)
		out = subprocess.check_output(args)
		if not sensitive_args:
			logger.info(out)
		return out
	except subprocess.CalledProcessError as e:
		logger.error("Command failed: {} \n{}".format(logged_cmd_str, e.output))
		if sensitive_args:
			raise Exception("Command {} failed".format(logged_cmd_str))
		raise e


def ensure_typed_aws_error(e, _type):
	if not e.response.get("Error", {}).get("Code") == _type:
		raise e
