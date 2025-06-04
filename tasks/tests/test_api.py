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
	'never':      None,

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
	EXPECTED_SQL_QUERY_COUNT_FOR_GET_DETAIL: int = 1


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
		self.make_task_detail_url = lambda task_pk: reverse('task-detail', args = [task_pk])
		self.make_comments_list_url = lambda task_pk: reverse('task-comments', args = [task_pk])


	# MARK: Get list
	# TODO: все места с user = superuser заменить на огромный цикл for с
	# перебором regular user, pm_user и superuser
	def test_get_list_from_anonymous(self):
		"""Проверяет, что аноним не может просмотреть список задач."""
		expected_key: str = 'detail'
		response: Response = self.client.get(self.tasks_list_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))


	def test_get_list_from_regular_user(self):
		"""
		Проверяет, что при запросе regular_user на task-list в ответе будут только те задачи, где
		он - assigned_to / created_by.
		"""
		user = self.user_1
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data: dict = TaskSerializer(
			self.default_qs.filter(Q(created_by = user) | Q(assigned_to = user)),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))
		
		for task_data in response.data:
			task = Task.objects.get(pk = task_data['id'])
			self.assertTrue(task.created_by == user or task.assigned_to == user,
				to_verbose_data(
					user = user,
					task_created_by = task.created_by,
					task_assigned_to = task.assigned_to)
			)


	def test_get_list_from_pm_and_superuser(self):
		"""
		Проверяет, что при запросе на task-list с уч. записи pm_user или superuser
		будут возвращены все задачи.
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			response: Response = self.client.get(self.tasks_list_url)

			expected_data: dict = TaskSerializer(
				self.default_qs,
				many = True
			).data


			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response, expected_data, user, here='Response Data, Expected Data & User'))
			self.assertEqual(len(response.data), Task.objects.count())


	#MARK: Advanced get list
	def test_get_list_with_ordering_by_due_date(self):
		"""
		Проверяет, что при сортировке по due_date в запросе, в ответе записи будут отсортированны по
		is_completed, due_date (выполненные в конце, те, у которых скоро дедлайн - в начале, невыполненные
		и просроченные - самые первые).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query = {
				'ordering': 'due_date', # сначала невыполненные, со скорым дедлайном
			}

			response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

			expected_data: dict = TaskSerializer(
				Task.objects.order_by('is_completed,due_date'),
				many = True
			).data
			


			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, user, here='Response Data, Expected Data & User'))


	def test_get_list_with_ordering_by_revert_due_date(self):
		"""
		Проверяет, что при сортировке по -due_date в запросе, в ответе записи будут отсортированны по
		is_completed, -due_date (выполненные в конце, те, у которых дедлайн позже всех - в начале).
		"""
		for user in [self.pm_user, self.superuser]:
			self.client.force_login(user)

			url_query = {
				'ordering': '-due_date',
			}

			response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

			expected_data: dict = TaskSerializer(
				Task.objects.order_by('is_completed,-due_date'),
				many = True
			).data
			


			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data, expected_data,
				to_verbose_data(response.data, expected_data, here='Response Data & Expected Data', user = user))


	def test_get_list_with_filtering(self):
		"""
		Проверяет, что фильтрация по is_completed & priority корректна.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'is_completed': False,
			'priority': Task.Priority.HIGH,
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			self.default_qs.filter(is_completed = False, priority = Task.Priority.HIGH),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_with_filtering_by_assigned_user(self):
		"""
		Проверяет, что фильтрация по assigned_to работает корректно.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'assigned_to': str(self.user_2.pk),
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			self.default_qs.filter(assigned_to = self.user_2.pk),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))
		
	
	def test_get_list_with_filtering_by_assigned_user_is_none(self):
		"""
		Проверяет, что фильтрация по assigned_to работает корректно.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'assigned_to': None,
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			self.default_qs.filter(assigned_to = None),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_with_search(self):
		"""
		Проверяет, что при запросе с поиском по for, будут возвращены все записи с for в названии или
		описании.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'search': 'for'
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			[
				self.superuser_tasks['Superuser Task for PM'],
				self.pm_user_tasks['PM Own Task 1'],
				self.pm_user_tasks['PM Task 3 for User3'],
				self.pm_user_tasks['PM Task 2 for User3'],
				self.pm_user_tasks['PM Task 1 for User3'],
				self.pm_user_tasks['PM Task 2 for User2'],
				self.pm_user_tasks['PM Task 1 for User2'],
			],
			many = True
		).data

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_with_filtering_ordering_and_search(self):
		"""
		Проверяет, что при фильтрации по priority, is_completed, сортировке по created_at и поиску
		по 'for' с уч. записи superuser в ответе будут все записи соответствующие запросу.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'is_completed': False,
			'priority': Task.Priority.HIGH,
			'ordering': 'created_at', # сначала старые
			'search':   'for',
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			[
				self.pm_user_tasks['PM Task 2 for User2'],
				self.pm_user_tasks['PM Task 3 for User3'],
				self.superuser_tasks['Superuser Task for PM']
			],
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_with_filtering_ordering_and_search_from_regular_user(self):
		"""
		Проверяет, что при фильтрации по priority, is_completed, сортировке по created_at и поиску
		по 'for' с уч. записи superuser в ответе будут все записи соответствующие запросу, где
		created_by / assigned_to == user_2 (т.е к которым у него есть доступ).
		"""
		user = self.user_2
		self.client.force_login(user)

		url_query = {
			'is_completed': False,
			'priority': Task.Priority.HIGH,
			'ordering': 'created_at', # сначала старые
			'search':   'for',
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			[
				self.pm_user_tasks['PM Task 2 for User2'],
			],
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_filtered_with_wrong_priority(self):
		"""
		Проверяет, что при фильтрации по неправильной приоритетности (invalid) в ответе
		ничего не будет т.к записей с такой приоритетностью не существует.
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'priority': 'invalid', # Not valid
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		# Все записи, где priority = invalid (то есть никакие)
		expected_data: list = []

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_filtered_with_not_valid_value_in_is_completed(self):
		"""
		Проверяет, что если передать в фильтрации в поле типа boolean строку "foo" -
		сервер выдаст ошибку 400, а не пустой список.
		"""

		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'is_completed': 'invalid',
		}
		expected_key: str = 'is_completed'

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))


	def test_get_list_filtered_with_not_exists_assigned_user(self):
		"""
		Проверяет, что при фильтрации по assigned_to с указанием несуществующего пользователя
		в ответе будет пустой список (так как таких записей не существует).
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'is_completed': False, # Valid
			'assigned_to': '999',  # None exists user
		}
		expected_data: list = []

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		# "Нашёл" все записи, где priority = invalid (то есть ничего не нашёл)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_ordered_with_ordering_by_not_exists_field(self):
		"""
		Проверяет, что при попытке получить через API отсортированный список задач с неправильным полем
		для сортировки - ответ будет отсортирован по умолчанию (проигнорируется).
		"""
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'ordering': 'none_exsists_field', # Not valid
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data: dict = TaskSerializer(
			self.default_qs,
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


	def test_get_list_sql_efficiency(self):
		"""Проверяет, что количество sql запросов на task-list соответствует ожидаемому."""
		user = self.superuser
		self.client.force_login(user)

		with CaptureQueriesContext(connection) as queries:
			responce: Response = self.client.get(self.tasks_list_url)

			self.assertEqual(len(queries), self.EXPECTED_SQL_QUERY_COUNT_FOR_GET_LIST)

	# MARK: Get detail
	def test_get_detail_from_anonymous(self):
		"""Проверяет, что аноним не может получить задачу."""
		task = self.user_1_tasks['Task 1']
		expected_key: str = 'detail'
		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(expected_key, response.data, to_verbose_data(response_data = response.data))


	def test_get_detail_from_owner_and_assigned_user(self):
		"""Проверяет, что владелец задачи может получить task-detail своей задачи."""
		user = self.user_1
		task = self.user_1_tasks['Task 2']
		self.client.force_login(user)

		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		expected_data: dict = TaskSerializer(
			Task.objects.get(pk = task.pk)
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, here='Response Data & Expected Data'))


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
		last_task:  Task = Task.objects.order_by('id').last()
		
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
		self.assertEqual(Task.objects.order_by('id').last(), last_task,
			to_verbose_data(
				last_task     = Task.objects.order_by('id').last(),
				expected_task = last_task))
		self.assertEqual(Task.objects.count(), tasks_count)


	def test_create_from_regular_user(self):
		"""
		Проверяет, что обычный пользователь может создать задачу.
		"""
		user = self.user_1
		self.client.force_login(user)

		initial_tasks_count: int = Task.objects.count()
		initial_last_task:  Task = Task.objects.order_by('id').last()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
		}


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.order_by('id').last()
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
		initial_last_task:  Task = Task.objects.order_by('id').last()
		
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
		self.assertEqual(Task.objects.order_by('id').last(), initial_last_task, to_verbose_data(
			last_task = Task.objects.order_by('id').last(),
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
		initial_last_task:  Task = Task.objects.order_by('id').last()
		
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
		self.assertEqual(Task.objects.order_by('id').last(), initial_last_task, to_verbose_data(
			last_task = Task.objects.order_by('id').last(),
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
		initial_last_task:  Task = Task.objects.order_by('id').last()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
			'created_by': self.user_3.pk,
		}


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.order_by('id').last()
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
		initial_last_task:  Task = Task.objects.order_by('id').last()

		data: dict = {
			'title': 'Task 3',
			'priority': Task.Priority.MEDIUM,
			'description': 'This is a new task',
			'due_date': DUE_DATES['next week'],
			'assigned_to': self.user_3,
		}
		expected_user = self.user_3


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.order_by('id').last()
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
			initial_last_task:  Task = Task.objects.order_by('id').last()

			data: dict = {
				'title': 'Task 3',
				'priority': Task.Priority.MEDIUM,
				'description': 'This is a new task',
				'due_date': DUE_DATES['next week'],
				'assigned_to': self.user_3,
			}
			expected_user = self.user_3


			response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

			current_last_task = Task.objects.order_by('id').last()
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
			initial_last_task:  Task = Task.objects.order_by('id').last()

			data: dict = {
				'title': 'Task 3',
				'priority': Task.Priority.MEDIUM,
				'description': 'This is a new task',
				'due_date': DUE_DATES['next week'],
			}


			response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

			current_last_task = Task.objects.order_by('id').last()
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
		
		pass
		
	
	def test_update_from_owner_or_assigned_user(self):
		"""
		Проверка, что пользователь установленный в created_by или assigned_to
		может изменить задачу.
		"""
		pass

	def test_update_with_void_title(self):
		"""
		Проверка, что при попытке установить '' в title - мы получим ошибку 400.
		"""
		pass
	
	def test_update_with_not_exists_priority_level(self):
		"""
		Проверка, что при попытке присвоить задаче несуществующий уровень
		приоритетности - мы получим ошибку 400.
		"""
		pass
	
	def test_update_with_assigned_to_something_user_from_regular_user(self):
		"""
		Проверка, что обычный пользователь не может назначать других пользователей
		в assigned_to.
		"""
		pass
	
	def test_update_with_assigned_to_something_user_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ и superuser могут назначать других пользователей в assigned_to.
		"""
		pass


	# MARK: Deleting
	def test_delete_from_anonymous(self):
		"""
		Проверка, что аноним не может удалить задачу.
		"""
		pass

	# перебор regular user, pm & superuser, с их задачами через цикл for и tuple
	def test_delete_from_owner(self):
		"""
		Проверка, что владелец может удалить свою задачу.
		"""
		pass

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
