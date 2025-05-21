from rest_framework_simplejwt.tokens import RefreshToken, AccessToken


REFRESH_TOKEN_COOKIE_NAME: str = RefreshToken.token_type + '_token'
ACCESS_TOKEN_COOKIE_NAME:  str = AccessToken.token_type  + '_token'
TOKEN_COOKIE_PARAMS: dict = {
	'samesite': 'Strict',
	'httponly': True,
	'secure':   True,
}