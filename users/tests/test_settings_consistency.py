from django.test import TestCase
from django.conf import settings as django_settings

from users import _settings


class LocalSettingsTest(TestCase):
	def setUp(self):
		self.SIMPLE_JWT: dict = django_settings.SIMPLE_JWT

	def test_cookie_params_consistency(self):
		SIMPLE_JWT: dict = self.SIMPLE_JWT

		testing_keys_mapping: dict = {
			'AUTH_COOKIE_SAMESITE': 'samesite',
			'AUTH_COOKIE_HTTPONLY': 'httponly',
			'AUTH_COOKIE_SECURE':   'secure',
			'AUTH_COOKIE_PATH':     'path',
			'AUTH_COOKIE_DOMAIN':   'domain',
		}

		for key in SIMPLE_JWT.keys():
			if key not in testing_keys_mapping: continue
			
			self.assertEqual(
				SIMPLE_JWT[key],
				_settings.TOKEN_COOKIE_PARAMS[testing_keys_mapping[key]]
			)

	
	def test_cookie_token_names(self):
		self.assertEqual(
			self.SIMPLE_JWT.get('AUTH_COOKIE'),
			_settings.ACCESS_TOKEN_COOKIE_NAME
		)

		self.assertEqual(
			self.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH'),
			_settings.REFRESH_TOKEN_COOKIE_NAME
		)
