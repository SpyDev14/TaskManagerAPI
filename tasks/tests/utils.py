from datetime import datetime, timedelta
from typing   import Any, Literal
from copy     import copy
import json
import re

from django.contrib.auth             import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test             import APIClient, APITestCase
from django.db.models        import QuerySet

from django.urls             import reverse
from django.utils            import timezone

from tasks.models import Task, Comment
from tasks.views  import TaskViewSet
from users.models import User as _User # для аннотации
from users        import local_settings

User: type[_User] = get_user_model()



class CookieJWTDebugClient(APIClient):
	def force_login(self, user):
		"""Force authentication with JWT tokens via cookies"""

		refresh = RefreshToken.for_user(user)

		self.cookies[local_settings.ACCESS_TOKEN_COOKIE_NAME]  = str(refresh.access_token)
		self.cookies[local_settings.REFRESH_TOKEN_COOKIE_NAME] = str(refresh)

class CustomAPITestCase(APITestCase):
	client_class = CookieJWTDebugClient
	
	DUE_DATES: dict[str, datetime | None] = {
		'never': None,

		'in a month':    timezone.now() + timedelta(days = 30),
		'this month':    timezone.now() + timedelta(days = 14),
		'next week':     timezone.now() + timedelta(days = 7),
		'tomorrow':      timezone.now() + timedelta(days = 1),
		'today':         timezone.now().replace(hour = 23, minute = 59),
		'in an 6 hours': timezone.now() + timedelta(hours = 6),
		'hour ago':      timezone.now() - timedelta(hours = 1),
		'yesterday':     timezone.now() - timedelta(days  = 1),
		'week ago':      timezone.now() - timedelta(days  = 7),
	}

	def setUp(self):
		users = [
			User.objects.create(
				username = f'Regular User {i}',
				password = 'password12345',
				role = User.Role.PROJECT_MANAGER,
			) for i in range(1, 4) # 1, 2, 3
		]

		self.user_1: _User = users[0]
		self.user_2: _User = users[1]
		self.user_3: _User = users[2]

		self.pm_user   = User.objects.create(
			username = 'ProjectManager',
			password = 'password12345',
			role = User.Role.PROJECT_MANAGER,
		)
		self.superuser = User.objects.create(
			username = 'Superuser',
			password = 'password12345',
			role = User.Role.REGULAR_USER,
			is_staff = True,
			is_superuser = True,
		)

		self.user_1_tasks: dict[Literal['Task 1', 'Task 2'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_1,
				title      = 'Task 1',
				priority   = Task.Priority.MEDIUM,
				due_date   = self.DUE_DATES['tomorrow'], 
			),
			'Task 2': Task.objects.create(
				created_by = self.user_1,
				title      = 'Task 2',
				priority   = Task.Priority.LOW,
				due_date   = self.DUE_DATES['week ago'],
			),
		}

		self.user_2_tasks: dict[Literal['Task 1', 'Task 2'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 1',
				priority = Task.Priority.MEDIUM,
				due_date = self.DUE_DATES['in a month'],
				is_completed = True,
			),
			'Task 2': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 2',
				priority = Task.Priority.LOW,
				due_date = self.DUE_DATES['never'],
			),
		}

		self.user_3_tasks: dict[Literal['Task 1'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_3,
				title = 'Task 1',
				priority = Task.Priority.HIGH,
				due_date = self.DUE_DATES['never'],
			),
		}

		self.pm_user_tasks: dict[Literal[
				'PM Task 1 for User2', 'PM Task 2 for User2',
				'PM Task 1 for User3', 'PM Task 2 for User3', 'PM Task 3 for User3',
				'PM Task 1 for Superuser',
				'PM Unassigned Task 1','PM Unassigned Task 2',
				'PM Own Task 1'
			], Task] = {

			'PM Task 1 for User2':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_2,
				title = 'PM Task 1 for User2',
				priority = Task.Priority.MEDIUM,
				due_date = self.DUE_DATES['tomorrow'],
				is_completed = True,
			),
			'PM Task 2 for User2':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_2,
				title = 'PM Task 2 for User2',
				priority = Task.Priority.HIGH,
				due_date = self.DUE_DATES['next week'],
			),
			'PM Task 1 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 1 for User3',
				priority = Task.Priority.MEDIUM,
				due_date = self.DUE_DATES['yesterday'],
			),
			'PM Task 2 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 2 for User3',
				priority = Task.Priority.LOW,
				due_date = self.DUE_DATES['week ago'],
				is_completed = True,
			),
			'PM Task 3 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 3 for User3',
				priority = Task.Priority.HIGH,
				due_date = self.DUE_DATES['yesterday'],
			),
			'PM Task 1 for Superuser': Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.superuser,
				title = 'PM Task 1 for Superuser',
				priority = Task.Priority.MEDIUM,
				due_date = self.DUE_DATES['week ago'],
				is_completed = True,
			),
			'PM Unassigned Task 1': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 1',
				priority = Task.Priority.LOW,
				due_date = self.DUE_DATES['tomorrow'],
			),
			'PM Unassigned Task 2': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 2',
				priority = Task.Priority.LOW,
				due_date = self.DUE_DATES['never'],
			),
			'PM Own Task 1':        Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.pm_user,
				title = 'PM Own Task 1',
				description = 'TASKFORME',
				priority = Task.Priority.HIGH,
				due_date = self.DUE_DATES['in an 6 hours'],
				is_completed = True,
			),
		}

		self.superuser_tasks: dict[Literal['Superuser Task 1', 'Superuser Task for PM'], Task] = {
			'Superuser Task 1': Task.objects.create(
				created_by = self.superuser,
				title = 'Superuser Task 1',
				priority = Task.Priority.LOW,
				due_date = self.DUE_DATES['never'],
			),
			'Superuser Task for PM': Task.objects.create(
				created_by = self.superuser,
				assigned_to = self.pm_user,
				title = 'Superuser Task for PM',
				priority = Task.Priority.HIGH,
				due_date = self.DUE_DATES['in a month'],
			),
		}

		[ # comments
			*[ # User 1 Tasks
				*[ # Task 1
					Comment.objects.create(
						task = self.user_1_tasks['Task 1'],
						created_by = self.user_1,
						content = 'Debug Content 1',
					),

					Comment.objects.create(
						task = self.user_1_tasks['Task 1'],
						created_by = self.user_1,
						content = 'Debug Content 2',
					),

					Comment.objects.create(
						task = self.user_1_tasks['Task 1'],
						created_by = self.pm_user,
						content = 'Debug PM Content 1',
					),
				],

				*[ ], # Task 2
			],

			*[ # User 2 Tasks
				*[ ], # Task 1

				*[ # Task 2
					Comment.objects.create(
						task = self.user_2_tasks['Task 2'],
						created_by = self.user_2,
						content = 'Debug Content 1',
					),
				],
			],

			*[ # User 3 Tasks
				*[ ], # Task 1
			],

			*[ # PM Tasks
				*[ ], # For User 1

				*[ # For User 2
					*[ ], # Task 1

					*[ # Task 2
						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 2 for User2'],
							created_by = self.user_2,
							content = 'Debug Content 1',
						),

						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 2 for User2'],
							created_by = self.user_2,
							content = 'Debug Content 2',
						),

						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 2 for User2'],
							created_by = self.user_2,
							content = 'Debug Content 3',
						),
					],
				],

				*[ # For User 3
					*[ # Task 1
						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 1 for User3'],
							created_by = self.user_3,
							content = 'Debug Content 1',
						),

						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 1 for User3'],
							created_by = self.user_3,
							content = 'Debug Content 2',
						),
					],

					*[ ], # Task 2

					*[ # Task 3
						Comment.objects.create(
							task = self.pm_user_tasks['PM Task 3 for User3'],
							created_by = self.user_3,
							content = 'Debug Content 1',
						),
					],
				],

				*[ # Unassigned
					*[ # Task 1
						Comment.objects.create(
							task = self.pm_user_tasks['PM Unassigned Task 1'],
							created_by = self.pm_user,
							content = 'Debug PM Content 1',
						),
					],

					*[ # Task 2
						Comment.objects.create(
							task = self.pm_user_tasks['PM Unassigned Task 2'],
							created_by = self.pm_user,
							content = 'Debug PM Content 1',
						),

						Comment.objects.create(
							task = self.pm_user_tasks['PM Unassigned Task 2'],
							created_by = self.pm_user,
							content = 'Debug PM Content 2',
						),
					]

				],

				*[ # PM Own tasks
					Comment.objects.create(
						task = self.pm_user_tasks['PM Own Task 1'],
						created_by = self.pm_user,
						content = 'Debug PM Content 1',
					),

					Comment.objects.create(
						task = self.pm_user_tasks['PM Own Task 1'],
						created_by = self.pm_user,
						content = 'Debug PM Content 2',
					),

					Comment.objects.create(
						task = self.pm_user_tasks['PM Own Task 1'],
						created_by = self.pm_user,
						content = 'Debug PM Content 3',
					),

					Comment.objects.create(
						task = self.pm_user_tasks['PM Own Task 1'],
						created_by = self.pm_user,
						content = 'Debug PM Content 4',
					),
				]
			],

			*[ # Superuser Tasks
				*[ ], # Task 1

				*[ # Task for PM
					Comment.objects.create(
						task = self.superuser_tasks['Superuser Task for PM'],
						created_by = self.pm_user,
						content = 'Debug PM Content 1',
					),

					Comment.objects.create(
						task = self.superuser_tasks['Superuser Task for PM'],
						created_by = self.superuser,
						content = 'Debug Superuser Content 1',
					),
				],
			],
		]



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
	do_not_serialize_fields: list[str] | Literal['__all__'] = [],
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
			perform_serialization: bool = (
				(header not in do_not_serialize_fields) and
				(do_not_serialize_fields != '__all__')
			)

			data = (
				json.dumps(value, indent = 4, ensure_ascii = False)
				if perform_serialization
				else value
			)
			if len(data) > 3000:
				data = (
					json.dumps(value, ensure_ascii = False)
					if perform_serialization
					else value
				)
		except TypeError:
			data = repr(value)
			data = re.sub(
				r'<(\w+):\s', 
				f'<{_COLORS['green']}\\1{_COLORS['reset']}: ', 
				data
			)

		# Обработка ключей (формат '"key":')
		data = re.sub(
			r'\"(\w+)\"\s*:', 
			f'{TOKEN_COLORS["key"]}"\\1"{_COLORS["reset"]}:', 
			data
		)
		
		# Обработка строк (формат ': "value"')
		data = re.sub(
			r':\s*\"(.*?)\"', 
			f': {TOKEN_COLORS["string"]}"\\1"{_COLORS["reset"]}', 
			data
		)
		
		# Обработка чисел (формат ': 123')
		data = re.sub(
			r'\"\s*:\s*([0-9]+(\.[0-9]+)?)', 
			f'": {TOKEN_COLORS["number"]}\\1{_COLORS["reset"]}', 
			data
		)			
		
		# Обработка true/false/null
		true_false_null_mapping: dict[str, str] = {
			'true':  f'{TOKEN_COLORS["bool"]}true{  _COLORS["reset"]}',
			'false': f'{TOKEN_COLORS["bool"]}false{ _COLORS["reset"]}',
			'null':  f'{TOKEN_COLORS["null"]}null{  _COLORS["reset"]}',
		}

		data = data.replace(": true",  f': {true_false_null_mapping["true"]}')
		data = data.replace(": false", f': {true_false_null_mapping["false"]}')
		data = data.replace(": null",  f': {true_false_null_mapping["null"]}')


		# Обработка случаев, когда это был не словарь и не список
		if data.isdigit():
			data = f'{TOKEN_COLORS["number"]}{data}{_COLORS['reset']}'

		# Если это строка
		data = re.sub(
			r'^\"([\s\S]*)\"$', 
			f'{TOKEN_COLORS["string"]}"\\1"{_COLORS["reset"]}', 
			data
		)

		data = true_false_null_mapping.get(data, data)

		data_for_print[f'\033[1;34m{header.replace('_', ' ').capitalize()}:\033[0m'] = f'{data}\033[0m'


	exit_string_parts: list[str] = []
	for header, data in data_for_print.items():
		exit_string_parts.append('\n')
		exit_string_parts.append(header)
		exit_string_parts.append(data)

	assembled_warning_messages: str = '\n'.join([f'{_COLORS["light yellow"]}Warning! {warning}{_COLORS['reset']}' for warning in warning_messages])
	return f'{assembled_warning_messages}{'\n'.join(exit_string_parts)}'
