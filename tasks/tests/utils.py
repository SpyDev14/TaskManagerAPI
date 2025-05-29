import json
from typing import Any, Iterable, Literal

from django.contrib.auth             import get_user_model
from django.test                     import TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test             import APIClient

from tasks.models import Task, Comment
from users.models import User as _User
from users        import local_settings

User: type[_User] = get_user_model()

class CookieJWTDebugClient(APIClient):
	def force_login(self, user):
		"""Force authentication with JWT tokens via cookies"""

		refresh = RefreshToken.for_user(user)

		self.cookies[local_settings.ACCESS_TOKEN_COOKIE_NAME]  = str(refresh.access_token)
		self.cookies[local_settings.REFRESH_TOKEN_COOKIE_NAME] = str(refresh)


def to_verbose_data(*args, resp_n_expected_here: bool = False, **kwargs) -> str | None:
	if not args and not kwargs:
		return None

	data_for_performing: dict[str, Any] = {}


	data_for_performing.update(kwargs)
	for i in range(len(args)-1):
		header = f'Element {i}'

		if resp_n_expected_here and i < 2:
			header = ['Response data', 'Expected data'][i]

		data_for_performing[header] = args[i]


	data_for_print: dict[str, str] = {}
	for index, value in data_for_performing.items():
		if hasattr(value, 'data'):
			value = value.data

		try:
			data = (
				json.dumps(value, indent = 4, ensure_ascii = False)
					.replace('"', '\033[1;33m"')
					.replace('\033[1;33m":', '"\033[0m:')
					.replace('\033[1;33m",', '"\033[0m,')
					.replace('"\n', '"\033[0m\n')
					.replace('"', '\'')
			)
		except:
			data = repr(value)

		data_for_print[f'\033[1;34m{index.replace('_', ' ').capitalize()}:\033[0m'] = data


	exit_string_parts: list[str] = []
	for header, data in data_for_print.items():
		exit_string_parts.append('\n')
		exit_string_parts.append(header)
		exit_string_parts.append(data)

	return '\n'.join(exit_string_parts)

def last_arr_index(iterable: Iterable):
	return len(iterable)-1

def last_arr_el(iterable: Iterable):
	return iterable[last_arr_index(iterable)]

def make_array_range(iterable: Iterable):
	return range(0, last_arr_index(iterable))
