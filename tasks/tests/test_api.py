from typing import Literal
from copy   import copy

from django.http.response    import HttpResponse
from django.contrib.auth     import get_user_model
from django.test.utils       import CaptureQueriesContext
from django.db.models        import Q, QuerySet
from django.db               import connection
from django.urls             import reverse
from rest_framework.response import Response
from rest_framework.test     import APITestCase
from rest_framework          import status

from tasks.tests.utils import CookieJWTDebugClient, to_verbose_data, setUpBase
from tasks.serializers import TaskSerializer
from tasks.models      import Task, Comment
from tasks.views       import TaskViewSet
from users.models      import User as _User

User: type[_User] = get_user_model()




class TaskAPITest(APITestCase):
	client_class = CookieJWTDebugClient

	# Только задачи
	EXPECTED_SQL_QUERY_COUNT_FOR_GET_LIST: int = 1
	# Задача и комментарии
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
				priority   = Task.Priority.MEDIUM
			),
			'Task 2': Task.objects.create(
				created_by = self.user_1,
				title      = 'Task 2',
				priority   = Task.Priority.LOW
			),
		}

		self.user_2_tasks: dict[Literal['Task 1', 'Task 2'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 1',
				priority = Task.Priority.MEDIUM
			),
			'Task 2': Task.objects.create(
				created_by = self.user_2,
				title = 'Task 2',
				priority = Task.Priority.LOW
			),
		}

		self.user_3_tasks: dict[Literal['Task 1'], Task] = {
			'Task 1': Task.objects.create(
				created_by = self.user_3,
				title = 'Task 1',
				priority = Task.Priority.HIGH
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
				is_completed = True,
			),
			'PM Task 2 for User2':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_2,
				title = 'PM Task 2 for User2',
				priority = Task.Priority.HIGH
			),
			'PM Task 1 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 1 for User3',
				priority = Task.Priority.MEDIUM,
			),
			'PM Task 2 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 2 for User3',
				priority = Task.Priority.LOW,
			),
			'PM Task 3 for User3':  Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.user_3,
				title = 'PM Task 3 for User3',
				priority = Task.Priority.HIGH,
			),
			'PM Unassigned Task 1': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 1',
				priority = Task.Priority.LOW,
			),
			'PM Unassigned Task 2': Task.objects.create(
				created_by = self.pm_user,
				title = 'PM Unassigned Task 2',
				priority = Task.Priority.LOW,
			),
			'PM Own Task 1':        Task.objects.create(
				created_by = self.pm_user,
				assigned_to = self.pm_user,
				title = 'PM Own Task 1',
				description = 'TASKFORME',
				priority = Task.Priority.HIGH,
				is_completed = True,
			),
		}

		self.superuser_tasks: dict[Literal['Superuser Task 1', 'Superuser Task for PM'], Task] = {
			'Superuser Task 1': Task.objects.create(
				created_by = self.superuser,
				title = 'Superuser Task 1',
				priority = Task.Priority.LOW
			),
			'Superuser Task for PM': Task.objects.create(
				created_by = self.superuser,
				assigned_to = self.pm_user,
				title = 'Superuser Task for PM',
				priority = Task.Priority.HIGH,
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
		response: Response = self.client.get(self.tasks_list_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIsNone(response.data)


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))
		
		for task_data in response.data:
			task = Task.objects.get(pk = task_data['id'])
			self.assertTrue(task.created_by == user or task.assigned_to == user,
				to_verbose_data(
					user = user,
					task_created_by = task.created_by,
					task_assigned_to = task.assigned_to)
			)


	def test_get_list_from_pm(self):
		"""
		Проверяет, что при запросе на task-list с уч. записи pm_user будут возвращены все
		задачи.
		"""
		user = self.pm_user
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data: dict = TaskSerializer(
			self.default_qs,
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response, expected_data, response_and_expected_here=True))
		self.assertEqual(len(response.data), Task.objects.count())


	def test_get_list_from_superuser(self):
		"""
		Проверяет, что при запросе на task-list с уч. записи superuser ответ будет аналогичен
		pm_user.
		"""
		user = self.superuser
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data: dict = TaskSerializer(
			self.default_qs,
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response, expected_data, response_and_expected_here=True))
		self.assertEqual(len(response.data), Task.objects.count())


	#MARK: Advanced get list
	def test_get_list_with_ordering_by_due_date(self):
		"""
		Проверяет, что при сортировке по due_date в запросе, в ответе записи будут отсортированны по
		is_completed, due_date (выполненные в конце, те, у которых скоро дедлайн - в начале, невыполненные
		и просроченные - самые первые).
		"""
		user = self.superuser
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


	def test_get_list_with_ordering_by_revert_due_date(self):
		"""
		Проверяет, что при сортировке по -due_date в запросе, в ответе записи будут отсортированны по
		is_completed, -due_date (выполненные в конце, те, у которых дедлайн позже всех - в начале).
		"""
		user = self.superuser
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))
		
	
	def test_get_list_with_filtering_by_not_assigned_user(self):
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIsNone(response.data)


	def test_get_list_filtered_with_none_exists_assigned_user(self):
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


	def test_get_list_ordered_with_bad_data(self):
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIsNone(response.data)


	def test_get_detail_from_owner(self):
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
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))
		

	def test_get_detail_from_assigned_user(self):
		"""Проверяет, что назначенный пользовательй может получить task-detail своей задачи."""
		user = self.user_2
		task = self.pm_user_tasks['PM Task 1 for User2']
		self.client.force_login(user)

		response: Response = self.client.get(self.make_task_detail_url(task.pk))

		expected_data: dict = TaskSerializer(
			Task.objects.get(pk = task.pk)
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, response_and_expected_here=True))


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
	# Где пользователи через or - там всё в цикле for с перебором пользователей,
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
			'description': 'New task',
		}

		
		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIsNone(response.data)
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
			'description': 'New task 123',
		}

		serializer = TaskSerializer(data = data)
		assert serializer.is_valid(raise_exception = True)

		expected_data: dict = serializer.data


		response: Response = self.client.post(self.tasks_list_url, data = data, format = 'json')

		current_last_task = Task.objects.order_by('id').last()
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, response_and_expected_here = True))
		self.assertNotEqual(current_last_task, initial_last_task,
			to_verbose_data(
				last_task     = initial_last_task,
				expected_task = expected_data))
		self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

		new_task = current_last_task
		self.assertEqual(new_task.description, 'New task 123')
		self.assertEqual(new_task.created_by, user)
		self.assertEqual(new_task.priority, Task.Priority.MEDIUM)


	def test_create_with_void_title(self):
		"""
		Проверка, что при попытке создания задачи с пустым заголовком мы получим ошибку 400.
		"""
		pass
	
	def test_create_with_wrong_priority(self):
		"""
		Проверка, что при попытке создать задачу с несуществующей приоритетностью мы получим
		ошибку 400.
		"""
		pass
	
	def test_create_with_created_by_in_data(self):
		"""
		Проверка, что при попытке создать задачу с указанием в body created_by - это поле
		проигнорируется (туда установится текущий пользователь).
		"""
		pass
	
	def test_create_with_assigned_to_something_user_from_regular_user(self):
		"""
		Проверка, что обычный пользователь не может назначить кого-то на задачу при создании и
		в это поле будет установлен он сам при создании.
		"""
		pass
	
	def test_create_with_assigned_to_something_user_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ может указать назначенного пользователя при создании.
		"""
		pass

	def test_create_without_assigned_to_in_data_from_pm_or_superuser(self):
		"""
		Проверка, что если ПМ не укажет никого в assigned_to, то в этом поле будет None.
		"""
		pass

# MARK: Updating
	def test_update_from_anonymous(self):
		"""
		Проверка, что аноним не может удалить задачу.
		"""
		pass
	
	# через for
	def test_update_from_owner_or_assigned_user(self):
		"""
		Проверка, что пользователь установленный в created_by или в assigned_to может удалить задачу.
		"""
		pass

	def test_update_with_void_title(self):
		"""
		Проверка, что при попытке установить '' в title - мы получим ошибку 400.
		"""
		pass
	
	def test_update_with_wrong_priority(self):
		"""
		Проверка, что нельзя присвоить задаче несуществующий уровень приоритетности.
		"""
		pass
	
	def test_update_with_assigned_to_something_user_from_regular_user(self):
		"""
		Проверка, что обычный пользователь не может назначать других пользователей в assigned_to.
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

	def test_delete_from_owner(self):
		"""
		Проверка, что владелец может удалить задачу.
		"""
		pass

	def test_delete_from_assigned_user(self):
		"""
		Проверка, что назначенный пользователь не может удалить задачу.
		"""
		pass

	def test_delete_from_pm_or_superuser(self):
		"""
		Проверка, что ПМ и суперпользователь могут удалить задачу.
		"""
		pass

	def test_delete_after_deleting(self):
		"""
		Проверка, что если попытаться удалить уже удалённую задачу - будет ошибка 404.
		"""
		pass
