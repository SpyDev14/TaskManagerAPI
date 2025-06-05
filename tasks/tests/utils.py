from typing import Any, Iterable, Literal
import json
import re

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

_COLORS: dict[str, str] = {
	'red':     '\033[31m',
	'green':   '\033[32m',
	'yellow':  '\033[33m',
	'blue':    '\033[34m',
	'magenta': '\033[35m',
	'cyan':    '\033[36m',

	'light red':     '\033[1;31m',
	'light green':   '\033[1;32m',
	'light yellow':  '\033[1;33m',
	'light blue':    '\033[1;34m',
	'light magenta': '\033[1;35m',
	'light cyan':    '\033[1;36m',

	'reset': '\033[0m'
}

def to_verbose_data(
	*args,
	here: Literal[
		'Response Data & Expected Data',
		'Response Data, Expected Data & User',
		'User, Response Data & Expected Data'
	] | None = None,
	do_not_serialize_this: list[str] | Literal['__all__'] = [],
	**kwargs) -> str | None:
	"""
	Автоматически попробует взять данные из аттрибута data
	"""

	if not args and not kwargs:
		return None
	
	warning_messages: list[str] = []
	
	# для обратной совместимости
	legacy_names_mapping: dict = {
		True: 'Response Data & Expected Data',
	}

	if here in legacy_names_mapping:
		here = legacy_names_mapping[here]
		warning_messages.append(f'here использует более не поддерживаемое значение!')

	data_for_performing: dict[str, Any] = {}

	header_renames_variants: dict[str | None, list] = {
		'Response Data & Expected Data':       ['Response data', 'Expected data'],
		'Response Data, Expected Data & User': ['Response data', 'Expected data', 'User'],
		'User, Response Data & Expected Data': ['User', 'Response data', 'Expected data'],
	}

	for i, arg in enumerate(args):
		header_renames = header_renames_variants.get(here, [])

		if here not in header_renames_variants:
			warning_messages.append(f'Значение here \'{here}\' не предусмотренно!')
		
		header = f'Element #{i+1}'

		if i < len(header_renames):
			header = header_renames[i]

		data_for_performing[header] = arg
	data_for_performing.update(kwargs)


	TOKEN_COLORS = {
		"key":    _COLORS['light blue'],
		"string": _COLORS['light red'],
		"number": _COLORS['light green'],
		"bool":   _COLORS['light cyan'],
		"null":   _COLORS['light magenta'],
	}

	data_for_print: dict[str, str] = {}
	for header, value in data_for_performing.items():
		if hasattr(value, 'data'):
			value = value
			warning_messages.append(
				'Был передан сам response или serializer (объект с аттрибутом'
				' data), в то время как ожидалась сама data!')

		try:
			json_str = (
				json.dumps(value, indent = 4, ensure_ascii = False)
				if header not in do_not_serialize_this and do_not_serialize_this != '__all__'
				else value
			)

			# Обработка ключей (формат '"key":')
			json_str = re.sub(
				r'\"(\w+)\"\s*:', 
				f'{TOKEN_COLORS["key"]}"\\1"{_COLORS["reset"]}:', 
				json_str
			)
			
			# Обработка строк (формат ': "value"')
			json_str = re.sub(
				r':\s*\"(.*?)\"', 
				f': {TOKEN_COLORS["string"]}"\\1"{_COLORS["reset"]}', 
				json_str
			)
			
			# Обработка чисел (формат ': 123')
			json_str = re.sub(
				r':\s*([0-9]+(\.[0-9]+)?)', 
				f': {TOKEN_COLORS["number"]}\\1{_COLORS["reset"]}', 
				json_str
			)			
			
			# Обработка true/false/null
			true_false_null_mapping: dict[str, str] = {
				'true':  f'{TOKEN_COLORS["bool"]}True{ _COLORS["reset"]}',
				'false': f'{TOKEN_COLORS["bool"]}True{ _COLORS["reset"]}',
				'null':  f'{TOKEN_COLORS["null"]}None{ _COLORS["reset"]}',
			}

			json_str = json_str.replace(": true",  f': {true_false_null_mapping["true"]}')
			json_str = json_str.replace(": false", f': {true_false_null_mapping["false"]}')
			json_str = json_str.replace(": null",  f': {true_false_null_mapping["null"]}')


			# Обработка случаев, когда это был не словарь и не список
			if json_str.isdigit():
				json_str = f'{TOKEN_COLORS["number"]}{json_str}{_COLORS['reset']}'

			# Если это строка
			# json_str = re.sub(
			# 	r'^"[\w\s\d]*"', 
			# 	f'{TOKEN_COLORS["string"]}"\\1"{_COLORS["reset"]}', 
			# 	json_str
			# )

			json_str = true_false_null_mapping.get(json_str, json_str)

			data = json_str			
		except:
			data = repr(value)


		data_for_print[f'\033[1;34m{header.replace('_', ' ').capitalize()}:\033[0m'] = f'{data}\033[0m'


	exit_string_parts: list[str] = []
	for header, data in data_for_print.items():
		exit_string_parts.append('\n')
		exit_string_parts.append(header)
		exit_string_parts.append(data)

	assembled_warning_messages: str = '\n'.join([f'{_COLORS["light yellow"]}Warning! {warning}{_COLORS['reset']}' for warning in warning_messages])
	return f'{assembled_warning_messages}{'\n'.join(exit_string_parts)}'

def last_arr_index(iterable: Iterable):
	return len(iterable)-1

def last_arr_el(iterable: Iterable):
	return iterable[last_arr_index(iterable)]

def make_array_range(iterable: Iterable):
	return range(0, last_arr_index(iterable))
