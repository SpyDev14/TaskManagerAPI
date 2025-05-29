from typing import Literal
from copy   import copy

from django.http.response    import HttpResponse
from django.contrib.auth     import get_user_model
from django.db.models        import Q
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

	def setUp(self):
		users = [
			User.objects.create(
				username = f'Regular User {i}',
				password = 'password12345',
				role = User.Role.PROJECT_MANAGER,
			) for i in range(1, 4) # 1, 2, 3
		]


		self.user_1 = users[0]
		self.user_2 = users[1]
		self.user_3 = users[2]

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
				'PM Unassigned Task 1','PM Unassigned Task 2','PM Own Task 1'
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



	def test_get_list_from_anonymous(self):
		response: Response = self.client.get(self.tasks_list_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIsNone(response.data)


	def test_get_list_normal(self):
		user = self.user_1
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data = TaskSerializer(
			Task.objects.filter(Q(created_by = user) | Q(assigned_to = user)),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, resp_n_expected_here=True))
		

	def test_get_list_from_pm(self):
		user = self.pm_user
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data = TaskSerializer(
			Task.objects.all(),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response, expected_data, resp_n_expected_here=True))


	def test_get_list_from_superuser(self):
		user = self.superuser
		self.client.force_login(user)

		response: Response = self.client.get(self.tasks_list_url)

		expected_data = TaskSerializer(
			Task.objects.all(),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response, expected_data, resp_n_expected_here=True))


	def test_get_list_with_ordering(self):
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'ordering': 'created_at', # сначала старые
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data = TaskSerializer(
			Task.objects.order_by('created_at'),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, resp_n_expected_here=True))
		

	def test_get_list_with_filtering(self):
		user = self.superuser
		self.client.force_login(user)

		url_query = {
			'is_completed': False,
			'priority': Task.Priority.HIGH,
		}

		response: Response = self.client.get(self.tasks_list_url, data = url_query, format = 'json')

		expected_data = TaskSerializer(
			Task.objects.filter(is_completed = False, priority = Task.Priority.HIGH),
			many = True
		).data


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, expected_data,
			to_verbose_data(response.data, expected_data, resp_n_expected_here=True))


	def test_get_list_advanced_with_bad_data(self):
		pass


	def test_get_list_sql_efficiency(self):
		pass


	def test_get_detail(self):
		pass




	def test_creating(self):
		pass


	def test_creating_with_wrong_data(self):
		pass



	def test_deleting(self):
		pass


