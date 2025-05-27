from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users import local_settings

class CookieJWTDebugClient(APIClient):
	def force_login(self, user):
		"""Force authentication with JWT tokens via cookies"""

		refresh = RefreshToken.for_user(user)
		
		self.cookies[local_settings.ACCESS_TOKEN_COOKIE_NAME]  = str(refresh.access_token)
		self.cookies[local_settings.REFRESH_TOKEN_COOKIE_NAME] = str(refresh)