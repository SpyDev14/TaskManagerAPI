from datetime import datetime, timedelta
from typing   import Literal
from copy     import copy

from django.http.response    import HttpResponse
from django.contrib.auth     import get_user_model
from django.test.utils       import CaptureQueriesContext
from django.db.models        import Q, QuerySet
from django.urls             import reverse
from django.db               import connection
from django.utils            import timezone
from rest_framework.response import Response
from rest_framework.test     import APITestCase
from rest_framework          import status

from tasks.tests.utils import CookieJWTDebugClient, to_verbose_data
from tasks.serializers import TaskSerializer
from tasks.models      import Task, Comment
from tasks.views       import TaskViewSet
from users.models      import User as _User # для аннотации

User: type[_User] = get_user_model()


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

class TaskAPITest(APITestCase):
	client_class = CookieJWTDebugClient

	# Только задачи
	EXPECTED_SQL_QUERY_COUNT_FOR_GET_LIST: int = 1
	# Задача и комментарии (но с оптимизацией всё равно 1)
	EXPECTED_SQL_QUERY_COUNT_FOR_GET_DETAIL: int = 2

	COMMENTS_FIELD_NAME: str = 'comments'


	def setUp(self):
		users = [
			User.objects.create(
				username = f'Regular User {i}',
				password = 'password12345',
				role = User.Role.PROJECT_MANAGER,
			) for i in range(1, 4) # 1, 2, 3
		]

		self.default_qs: QuerySet = TaskViewSet.get_queryset()

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
				due_date   = DUE_DATES['tomorrow'], 
			),
			'Task 2': Task.objects.create(
				created_by = self.user_1,
				title      = 'Task 2',
				priority   = Task.Priority.LOW,
				due_date   = DUE_DATES['week ago'],
			),
		}

		self.user_2_tasks: dict[Literal['Task 1', 'Task 2'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 1',
				priority = Task.Priority.MEDIUM,
				due_date = DUE_DATES['in a month'],
				is_completed = True,
			),
			'Task 2': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 2',
				priority = Task.Priority.LOW,
				due_date = DUE_DATES['never'],
			),
		}

		self.user_3_tasks: dict[Literal['Task 1'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_3,
				title = 'Task 1',
				priority = Task.Priority.HIGH,
				due_date = DUE_DATES['never'],
			),
		}

		self.pm_user_tasks: dict[Literal[
				'PM Task 1 for User2', 'PM Task 2 for User2',
				'PM Task 1 for User3', 'PM Task 2 for User3', 'PM Task 3 for User3',
				'PM Unassigned Task 1','PM Unassigned Task 2',
				'PM Own Task 1'
			], Task] = {

			'PM Task 1 for User2':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_2,
				title = 'PM Task 1 for User2',
				priority = Task.Priority.MEDIUM,
				due_date = DUE_DATES['tomorrow'],
				is_completed = True,
			),
			'PM Task 2 for User2':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_2,
				title = 'PM Task 2 for User2',
				priority = Task.Priority.HIGH,
				due_date = DUE_DATES['next week'],
			),
			'PM Task 1 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 1 for User3',
				priority = Task.Priority.MEDIUM,
				due_date = DUE_DATES['yesterday'],
			),
			'PM Task 2 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 2 for User3',
				priority = Task.Priority.LOW,
				due_date = DUE_DATES['week ago'],
				is_completed = True,
			),
			'PM Task 3 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 3 for User3',
				priority = Task.Priority.HIGH,
				due_date = DUE_DATES['yesterday'],
			),
			'PM Unassigned Task 1': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 1',
				priority = Task.Priority.LOW,
				due_date = DUE_DATES['tomorrow'],
			),
			'PM Unassigned Task 2': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 2',
				priority = Task.Priority.LOW,
				due_date = DUE_DATES['never'],
			),
			'PM Own Task 1':        Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.pm_user,
				title = 'PM Own Task 1',
				description = 'TASKFORME',
				priority = Task.Priority.HIGH,
				due_date = DUE_DATES['in an 6 hours'],
				is_completed = True,
			),
		}

		self.superuser_tasks: dict[Literal['Superuser Task 1', 'Superuser Task for PM'], Task] = {
			'Superuser Task 1': Task.objects.create(
				created_by = self.superuser,
				title = 'Superuser Task 1',
				priority = Task.Priority.LOW,
				due_date = DUE_DATES['never'],
			),
			'Superuser Task for PM': Task.objects.create(
				created_by = self.superuser,
				assigned_to = self.pm_user,
				title = 'Superuser Task for PM',
				priority = Task.Priority.HIGH,
				due_date = DUE_DATES['in a month'],
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


		self.tasks_list_url = reverse('task-list')
		self.make_task_detail_url = lambda task: reverse('task-detail', args = [getattr(task, 'pk', task)])
		self.make_comments_list_url = lambda task: reverse('task-comments', args = [getattr(task, 'pk', task)])


	# MARK: Get list
	# TODO: добавить проерку, что в get-list нет comments, а в get-detail есть
	# перебором regular user, pm_user и superuser
	def test_get_list_from_anonymous(self):
		"""Проверяет, что аноним не может просмотреть список задач."""
		expected_key: str = 'detail'
		response: Response = self.client.get(self.tasks_list_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response = response.data))


	def test_get_list_from_regular_user(self):
		"""
		Проверяет, что при запросе regular_user на task-list в ответе будут только те задачи, где
		он - assigned_to / created_by.
		"""
		user = self.user_1
		self.client.force_login(user)

		expected_data: list = TaskSerializer(
			self.default_qs.filter(Q(created_by = user) | Q(assigned_to = user)),
			many = True
		).data


		response: Response = self.client.get(self.tasks_list_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_from_pm_and_superuser(self):
		"""
		Проверяет, что при запросе на task-list с уч. записи pm_user или superuser
		будут возвращены все задачи.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			expected_data: list = TaskSerializer(
				self.default_qs,
				many = True
			).data


			response: Response = self.client.get(self.tasks_list_url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))
			self.assertEqual(len(response.data), Task.objects.count())


	def test_get_list_tasks_doesnt_contais_comments(self):
		"""
		Проверяет, что tasks в get-list не содержат комментариев.
		"""
		for user in [self.pm_user, self.superuser, self.user_1]:
			self.client.force_login(user)

			response: Response = self.client.get(self.tasks_list_url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertFalse(
				any((self.COMMENTS_FIELD_NAME in task_data) for task_data in response.data),
				to_verbose_data(
					do_not_serialize_this = ['message'],
					message = '\033[1;33mНекоторые задачи содержат комментарии',
					**{
						f'#{task_data['id']} {task_data['title']}': task_data
						for task_data in response.data
						if self.COMMENTS_FIELD_NAME in task_data
					}
				)
			)


	#MARK: Advanced get list
	def test_get_list_with_ordering_by_due_date(self):
		"""
		Проверяет, что при сортировке по due_date в запросе, в ответе записи будут отсортированны по
		is_completed, due_date (выполненные в конце, те, у которых скоро дедлайн - в начале, невыполненные
		и просроченные - самые первые).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			# сначала невыполненные, со скорым дедлайном
			url_query: str = 'ordering=due_date'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				self.default_qs.order_by('is_completed', 'due_date'),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_with_ordering_by_revert_due_date(self):
		"""
		Проверяет, что при сортировке по -due_date в запросе, в ответе записи будут отсортированны по
		is_completed, -due_date (выполненные в конце, те, у которых дедлайн позже всех - в начале).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'ordering=-due_date'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				Task.objects.all().order_by('is_completed', '-due_date'),
				many = True
			).data
			

			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_with_filtering(self):
		"""
		Проверяет, что фильтрация по is_completed & priority корректна.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = f'is_completed=false&priority={Task.Priority.HIGH}'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				self.default_qs.filter(is_completed = False, priority = Task.Priority.HIGH),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_with_filtering_by_assigned_user(self):
		"""
		Проверяет, что фильтрация по assigned_to работает корректно.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = f'assigned_to={self.user_2.pk}'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				self.default_qs.filter(assigned_to = self.user_2.pk),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))
		
	
	def test_get_list_with_filtering_by_assigned_user_is_none(self):
		"""
		Проверяет, что фильтрация по assigned_to работает корректно.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'assigned_to=null'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				self.default_qs.filter(assigned_to = None),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_with_search(self):
		"""
		Проверяет, что при запросе с поиском по for, будут возвращены все записи с for в названии или
		описании.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'ordering=created_at&search=for'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				Task.objects.filter(
					Q(title__icontains = 'for') | Q(description__icontains = 'for')
				),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_with_filtering_ordering_and_search(self):
		"""
		Проверяет, что при фильтрации по priority, is_completed, сортировке по created_at и поиску
		по 'for' с уч. записи superuser в ответе будут все записи соответствующие запросу.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			query_params: list[str] = [
				'is_completed=false',
				f'priority={Task.Priority.HIGH}',
				'ordering=created_at', # сначала старые
				'search=for',
			]

			url_query: str = '&'.join(query_params)
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				Task.objects
					.filter(is_completed = False, priority = Task.Priority.HIGH)
					.filter(Q(title__icontains = 'for') | Q(description__icontains = 'for'))
					.order_by('created_at'),
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_with_filtering_ordering_and_search_from_regular_user(self):
		"""
		Проверяет, что при фильтрации по priority, is_completed, сортировке по created_at и поиску
		по 'for' с уч. записи user_2 в ответе будут все записи соответствующие запросу, где
		created_by / assigned_to == user_2 (т.е к которым у него есть доступ).
		"""
		user = self.user_2
		self.client.force_login(user)

		query_params: list[str] = [
			'is_completed=false',
			f'priority={Task.Priority.HIGH}',
			'ordering=created_at', # сначала старые
			'search=for',
		]

		url_query: str = '&'.join(query_params)
		url:       str = f'{self.tasks_list_url}?{url_query}'

		expected_data: list = TaskSerializer(
			Task.objects
				.filter(is_completed = False, priority = Task.Priority.HIGH)
				.filter(Q(title__icontains = 'for') | Q(description__icontains = 'for'))
				.filter(Q(created_by = user) | Q(assigned_to = user))
				.order_by('created_at'),
			many = True
		).data


		response: Response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_filtered_with_wrong_priority(self):
		"""
		Проверяет, что при фильтрации по неправильной приоритетности (invalid) в ответе
		ничего не будет т.к записей с такой приоритетностью не существует.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'priority=invalid'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			# Все записи, где priority = invalid (то есть никакие)
			expected_data: list = []


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_filtered_with_not_valid_value_in_is_completed(self):
		"""
		Проверяет, что если передать в фильтрации в поле типа boolean строку "foo" -
		сервер выдаст ошибку 400, а не пустой список.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'is_completed=invalid'
			url:       str = f'{self.tasks_list_url}?{url_query}'
			expected_key: str = 'is_completed'


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
			self.assertIn(expected_key, response.data,
				to_verbose_data(user = user, response_data = response.data))


	def test_get_list_filtered_with_not_exists_assigned_user(self):
		"""
		Проверяет, что при фильтрации по assigned_to с указанием несуществующего пользователя
		в ответе будет пустой список (так как таких записей не существует).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'assigned_user=999'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			# Все записи, где assigned_user = 999 (то есть никакие)
			expected_data: list = []


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_ordered_with_ordering_by_not_exists_field(self):
		"""
		Проверяет, что при попытке получить через API отсортированный список задач с неправильным полем
		для сортировки - ответ будет отсортирован по умолчанию (проигнорируется).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query: str = 'ordering=none_exsists_field'
			url:       str = f'{self.tasks_list_url}?{url_query}'

			expected_data: list = TaskSerializer(
				self.default_qs,
				many = True
			).data


			response: Response = self.client.get(url)

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(user, response.data, expected_data, here='User, Response Data & Expected Data'))


	def test_get_list_sql_efficiency(self):
		"""Проверяет, что количество sql запросов на task-list соответствует ожидаемому."""
		for user in [self.pm_user, self.superuser, self.user_1]:
			self.client.force_login(user)

			with CaptureQueriesContext(connection) as queries:
				self.client.get(self.tasks_list_url)

				self.assertEqual(len(queries), self.EXPECTED_SQL_QUERY_COUNT_FOR_GET_LIST)


	# MARK: Get detail
	def test_get_detail_from_anonymous(self):
		"""Проверяет, что аноним не может получить задачу."""
		task = self.user_1_tasks['Task 1']
		expected_key: str = 'detail'

		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response = response.data))


	def test_get_detail_from_owner_and_assigned_user(self):
		"""Проверяет, что владелец задачи может получить task-detail своей задачи."""
		for user, task in [
			(self.user_1,    self.user_1_tasks['Task 1']),
			(self.pm_user,   self.pm_user_tasks['PM Own Task 1']),
			(self.superuser, self.superuser_tasks['Superuser Task 1'])
		]:
			self.client.force_login(user)

			expected_data: dict = TaskSerializer(
				Task.objects.get(pk = task.pk)
			).data


			response: Response = self.client.get(self.make_task_detail_url(task))

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_detail_has_task_comments(self):
		"""Проверяет, что в task-detail есть комментарии."""
		for user, task in [
			(self.user_1,    self.user_1_tasks['Task 1']),
			(self.pm_user,   self.pm_user_tasks['PM Own Task 1']),
			(self.superuser, self.superuser_tasks['Superuser Task 1'])
		]:
			self.client.force_login(user)

			response: Response = self.client.get(self.make_task_detail_url(task))

			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertIn(self.COMMENTS_FIELD_NAME, response.data)


	def test_get_detail_from_another_regular_user(self):
		"""Проверяет, что другой пользователь не может получить task-detail чужой задачи."""
		user = self.user_2
		task = self.user_1_tasks['Task 2']
		self.client.force_login(user)

		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertIsNone(response.data, to_verbose_data(response = response.data))


	def test_get_detail_sql_efficiency(self):
		"""Проверяет, что при запросе на task-detail количество sql запросов соответствует ожидаемому"""
		user = self.superuser
		task = self.user_1_tasks['Task 1']
		self.client.force_login(user)

		with CaptureQueriesContext(connection) as queries:
			responce: Response = self.client.get(self.make_task_detail_url(task.pk))

			self.assertEqual(len(queries), self.EXPECTED_SQL_QUERY_COUNT_FOR_GET_DETAIL)


	# MARK: Creating
	# Где пользователи через or/and - там всё в цикле for с перебором пользователей,
	# заодно косвенно авторизацию проверим.
	def test_create_from_anonymous(self):
		"""
		Проверяет, что аноним не может создать задачу.
		"""
		tasks_count: int = Task.objects.count()
		last_task:  Task = Task.objects.latest()
		
		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
		}
		expected_key: str = 'detail'
		
		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))
		self.assertEqual(Task.objects.latest(), last_task,
			to_verbose_data(
				last_task     = Task.objects.latest(),
				expected_task = last_task))
		self.assertEqual(Task.objects.count(), tasks_count)


	def test_create_from_regular_user(self):
		"""
		Проверяет, что обычный пользователь может создать задачу.
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.latest()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
		}


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.latest()
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertNotEqual(current_last_task, initial_last_task)
		self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

		new_task = current_last_task
		expected_data: dict = TaskSerializer(new_task).data
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here = 'Response Data & Expected Data'))
		self.assertEqual(new_task.created_by, user,
			to_verbose_data(this_user = user, task_owner = new_task.created_by))
		self.assertEqual(new_task.assigned_to, user,
			to_verbose_data(this_user = user, assigned_to_task_user = new_task.assigned_to))


	def test_create_with_void_title(self):
		"""
		Проверка, что при попытке создания задачи с пустым заголовком мы получим ошибку 400.
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.latest()
		
		data: dict = {
			'title': '',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
		}

		expected_key: str = 'title'

		
		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn(expected_key, response.data, to_verbose_data(
			expected_key = expected_key,
			response_data = response.data))
		self.assertEqual(Task.objects.latest(), initial_last_task, to_verbose_data(
			last_task = Task.objects.latest(),
			expected_task = initial_last_task))
		self.assertEqual(Task.objects.count(), initial_tasks_count)
	

	def test_create_with_not_exists_priority_level(self):
		"""
		Проверка, что при попытке создать задачу с несуществующей приоритетностью мы получим
		ошибку 400.
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.latest()
		
		data: dict = {
			'title': 'New task',
			'priority': 'invalid',
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
		}

		expected_key: str = 'priority'

		
		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn(expected_key, response.data, to_verbose_data(
			expected_key = expected_key,
			response_data = response.data))
		self.assertEqual(Task.objects.latest(), initial_last_task, to_verbose_data(
			last_task = Task.objects.latest(),
			expected_task = initial_last_task))
		self.assertEqual(Task.objects.count(), initial_tasks_count)
		

	def test_create_created_by_autoset_even_if_specified_in_the_body(self):
		"""
		Проверка, что при создании задачи в поле created_by всегда устанавливается
		пользователь, отправивший запрос, даже если поле created_by было указано в
		теле запроса и ссылалось на другого пользователя (то есть проигнорируется).
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.latest()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
			'created_by': self.user_3.pk,
		}


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.latest()
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertNotEqual(current_last_task, initial_last_task)
		self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

		new_task = current_last_task
		self.assertEqual(new_task.created_by, user,
			to_verbose_data(this_user = user, task_owner = new_task.created_by))

	
	def test_create_with_assigned_to_something_user_from_regular_user(self):
		"""
		Проверка, что обычный пользователь не может назначить кого-то на задачу при
		создании и в это поле автоматически будет установлен он сам.
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.latest()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
			'assigned_to': self.user_3,
		}
		expected_user = self.user_3


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.latest()
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertNotEqual(current_last_task, initial_last_task)
		self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

		new_task = current_last_task
		self.assertEqual(new_task.assigned_to, user,
			to_verbose_data(expected_user = expected_user, assigned_to_task_user = new_task.assigned_to))
	
	def test_create_with_assigned_to_something_user_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ и суперпользователь могут указать назначенного пользователя
		при создании.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			initial_tasks_count: int = Task.objects.count()
			initial_last_task:  Task = Task.objects.latest()

			data: dict = {
				'title': 'Task 3',
				'priority': Task.Priority.MEDIUM,
				'description': 'This is a new task',
				'due_date': DUE_DATES['next week'],
				'assigned_to': self.user_3,
			}
			expected_user = self.user_3


			response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

			current_last_task = Task.objects.latest()
			self.assertEqual(response.status_code, status.HTTP_201_CREATED)
			self.assertNotEqual(current_last_task, initial_last_task)
			self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

			new_task = current_last_task
			expected_data: dict = TaskSerializer(new_task).data
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, here = 'Response Data & Expected Data'))
			self.assertEqual(new_task.created_by, user,
				to_verbose_data(this_user = user, task_owner = new_task.created_by))
			self.assertEqual(new_task.assigned_to, user,
				to_verbose_data(expected_user = expected_user, assigned_to_task_user = new_task.assigned_to))
		

	def test_create_without_assigned_to_in_data_from_pm_or_superuser(self):
		"""
		Проверка, что если ПМ или суперпользователь не укажет никого в assigned_to,
		в этом поле будет None. Также проверяет создание в принципе.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			initial_tasks_count: int = Task.objects.count()
			initial_last_task:  Task = Task.objects.latest()

			data: dict = {
				'title': 'Task 3',
				'priority': Task.Priority.MEDIUM,
				'description': 'This is a new task',
				'due_date': DUE_DATES['next week'],
			}


			response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

			current_last_task = Task.objects.latest()
			self.assertEqual(response.status_code, status.HTTP_201_CREATED)
			self.assertNotEqual(current_last_task, initial_last_task)
			self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

			new_task = current_last_task
			expected_data: dict = TaskSerializer(new_task).data
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, here = 'Response Data & Expected Data'))
			self.assertEqual(new_task.assigned_to, user,
				to_verbose_data(expected_user = None, assigned_to_task_user = new_task.assigned_to))

# MARK: Updating
	def test_update_from_anonymous(self):
		"""
		Проверка, что аноним не может изменить задачу.
		"""

		task = self.user_1_tasks['Task 1']

		data: dict = {
			'title': 'Changed title',
			'is_completed': True,
		}
		expected_key: str = 'detail'
		
		response: Response = self.client.patch(self.make_task_detail_url(task), data, content_type = 'application/json')

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data)
		self.assertEqual(Task.objects.get(pk = task.pk), task)
		
	
	def test_update_from_owner_or_assigned_user(self):
		"""
		Проверка, что пользователь установленный в created_by или assigned_to
		может изменить задачу.
		"""

		for user, task in [
			(self.pm_user, self.pm_user_tasks['PM Own Task 1']),
			(self.user_2,  self.pm_user_tasks['PM Task 1 for User2'])
		]:
			self.client.force_login(user)
			url  = self.make_task_detail_url(task)

			data: dict = {
				'title': f'[COMPLETED] {task.title}',
				'is_completed': True,
			}
			old_task = copy(task)


			response: Response = self.client.patch(url, data, content_type = 'application/json')

			task.refresh_from_db()
			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, TaskSerializer(task).data,
				to_verbose_data(response.data, TaskSerializer(task).data, here = 'Response Data & Expected Data'))
			self.assertNotEqual(task, old_task, to_verbose_data(task = TaskSerializer(task)))



	def test_update_with_void_title(self):
		"""
		Проверка, что при попытке установить '' в title - мы получим ошибку 400.
		"""
		user = self.superuser
		task = self.superuser_tasks['Superuser Task 1']

		self.client.force_login(user)

		data: dict = {
			'title': ''
		}
		expected_key = 'title'
		old_task = copy(task)

		response: Response = self.client.patch(self.make_task_detail_url(task), data, content_type='application/json')

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))
		self.assertEqual(task, old_task, to_verbose_data(task = TaskSerializer(task).data))


	def test_update_with_not_exists_priority_level(self):
		"""
		Проверка, что при попытке присвоить задаче несуществующий уровень
		приоритетности - мы получим ошибку 400.
		"""
		user = self.superuser
		task = self.superuser_tasks['Superuser Task 1']

		self.client.force_login(user)

		data: dict = {
			'priority': 'invalid'
		}
		expected_key = 'priority'
		old_task = copy(task)

		response: Response = self.client.patch(self.make_task_detail_url(task), data, content_type='application/json')

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))
		self.assertEqual(task, old_task,
			to_verbose_data(task = TaskSerializer(task).data, old_task = TaskSerializer(old_task).data))
		self.assertNotEqual(task.priority, 'invalid')

	
	def test_update_with_assigned_to_something_user_from_regular_user(self):
		"""
		Проверка, что обычный пользователь не может назначать других пользователей
		в assigned_to.
		"""
		user = self.user_1
		task = self.user_1_tasks['Task 1']

		self.client.force_login(user)

		data: dict = {
			'title': f'[UPDATED] {task.title}',
			'assigned_to': self.user_2,
		}
		old_task = copy(task)

		assert task.assigned_to == user

		response: Response = self.client.patch(self.make_task_detail_url(task), data, content_type='application/json')

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(task.assigned_to, user)
		self.assertNotEqual(task, old_task, to_verbose_data(task = TaskSerializer(task).data))

	
	def test_update_with_assigned_to_something_user_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ и superuser могут назначать других пользователей в assigned_to.
		"""
		task: Task
		for user, task in [
			(self.superuser, self.superuser_tasks['Superuser Task 1']),
			(self.pm_user,   self.pm_user_tasks['PM Unassigned Task 2']),
		]:
			assert task.assigned_to == None

			self.client.force_login(user)
			url = self.make_task_detail_url(task)

			data: dict = {
				'title': f'[UPDATED] {task.title}',
				'assigned_to': self.user_2,
			}
			old_task = copy(task)

			response: Response = self.client.patch(url, data, content_type='application/json')

			task.refresh_from_db()
			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(task.assigned_to, self.user_2)
			self.assertNotEqual(task, old_task, to_verbose_data(task = TaskSerializer(task).data))


	# MARK: Deleting
	def test_delete_from_anonymous(self):
		"""
		Проверка, что аноним не может удалить задачу.
		"""
		task = self.user_1_tasks['Task 1']
		expected_key: str = 'detail'
		initial_tasks_count: int = Task.objects.count()

		response: Response = self.client.delete(self.make_task_detail_url(task))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response = response.data))

		self.assertTrue(Task.objects.filter(pk = task.pk).exists())
		self.assertEqual(Task.objects.count(), initial_tasks_count)

		
	def test_delete_from_owner(self):
		"""
		Проверка, что владелец может удалить свою задачу.
		"""
		for user, task in [
			(self.user_1,    self.user_1_tasks['Task 1']),
			(self.pm_user,   self.pm_user_tasks['PM Own Task 1']),
			(self.superuser, self.superuser_tasks['Superuser Task 1'])
		]:
			self.client.force_login(user)
			url = self.make_task_detail_url(task)

			initial_tasks_count: int = Task.objects.count()
			

			response: Response = self.client.delete(url)

			self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
			self.assertIsNone(response.data, to_verbose_data(response = response.data))
			
			self.assertFalse(Task.objects.filter(pk = task.pk).exists())
			self.assertEqual(Task.objects.count(), initial_tasks_count - 1)


	def test_delete_from_assigned_user(self):
		"""
		Проверка, что назначенный пользователь не может удалить задачу.
		"""
		pass

	def test_delete_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ и суперпользователь могут удалить чужую задачу.
		"""
		pass

	def test_delete_after_deleting(self):
		"""
		Проверка, что если попытаться удалить уже удалённую задачу - будет ошибка 404.
		"""
		pass
