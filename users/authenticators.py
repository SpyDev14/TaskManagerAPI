from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http.request import HttpRequest

from . import settings as local_settings

class JWTFromCookiesAuthentication(JWTAuthentication):
	def authenticate(self, request: HttpRequest):
		raw_token = request.COOKIES.get(local_settings.ACCESS_TOKEN_COOKIE_NAME)

		if raw_token is None:
			return None
		
		validated_token = self.get_validated_token(raw_token.encode())
		return self.get_user(validated_token), validated_token