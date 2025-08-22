from typing import Literal
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.conf import settings

_SIMPLE_JWT: dict = settings.SIMPLE_JWT

REFRESH_TOKEN_COOKIE_NAME: str = RefreshToken.token_type + '_token'
ACCESS_TOKEN_COOKIE_NAME:  str = AccessToken.token_type  + '_token'
TOKEN_COOKIE_PARAMS: dict[Literal['samesite', 'httponly', 'secure', 'path', 'domain']] = {
    'samesite': _SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Strict'),
    'httponly': _SIMPLE_JWT.get('AUTH_COOKIE_HTTPONLY', True),
    'secure':   _SIMPLE_JWT.get('AUTH_COOKIE_SECURE', True),
    'path':     _SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
    'domain':   _SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None)
}


__all__ = [
	'REFRESH_TOKEN_COOKIE_NAME',
	'ACCESS_TOKEN_COOKIE_NAME',
	'TOKEN_COOKIE_PARAMS'
]
