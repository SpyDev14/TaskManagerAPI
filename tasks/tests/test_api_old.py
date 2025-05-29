from copy import copy

from django.http.response import HttpResponse
from django.db.models     import Q
from django.urls          import reverse
from rest_framework.test  import APITestCase
from rest_framework       import status

from users.tests.debug_client import CookieJWTDebugClient
from users.models             import User
from tasks.serializers        import TaskSerializer
from tasks.models             import Task
from tasks.views              import TaskViewSet

from tasks.tests.utils import to_verbose_data


class TaskAPITest(APITestCase):
	client_class = CookieJWTDebugClient

	def setUp(self):
		self.user1 = User.objects.create(
			username = 'RegularUser1',
			password = '12345'
		)

		self.user2 = User.objects.create(
			username = 'RegularUser2',
			password = '12345'
		)

		self.pm_user = User.objects.create(
			username = 'ProjectManager',
			password = '12345',
			role = User.Role.PROJECT_MANAGER
		)


		self.user1_task = Task.objects.create(
			title = 'User1 TestTask1',
			created_by = self.user1,
			priority = Task.Priority.MEDIUM,
		)


		self.user2_task = Task.objects.create(
			title = 'User2 TestTask1',
			created_by = self.user2,
			priority = Task.Priority.LOW,
		)

		self.pm_user_task = Task.objects.create(
			title = 'Project Manager Task',
			created_by = self.pm_user,
			priority = Task.Priority.HIGH,
		)

		self.tasks_url = reverse('task-list')
		self.get_task_detail_url = lambda pk: reverse('task-detail', args = [pk])


	def test_get(self):
		user = self.user1
		user_task = self.user1_task
		qs = TaskViewSet.queryset.filter(
			Q(created_by = user) | Q(assigned_to = user)
		)
		expected_data = TaskSerializer(qs, many = True).data

		# anonymous
		response: HttpResponse = self.client.get(self.tasks_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertNotEqual(response.data, expected_data)

		self.client.force_login(user)

		# regular user (его задачи)
		response: HttpResponse = self.client.get(self.tasks_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(response.data))
		self.assertEqual(response.data, expected_data, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user,
			user_task = user_task
		))


		expected_data = TaskSerializer(user_task).data

		response: HttpResponse = self.client.get(self.get_task_detail_url(user_task.pk))
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user
		))
		self.assertEqual(response.data, expected_data, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user
		))

		# PM (все задачи)
		user = self.pm_user
		user_task = self.pm_user_task
		self.client.force_login(user)

		response: HttpResponse = self.client.get(self.tasks_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(response.data))
		self.assertEqual(response.data, expected_data, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user,
			user_task = user_task
		))


		expected_data = TaskSerializer(user_task).data

		response: HttpResponse = self.client.get(self.get_task_detail_url(user_task.pk))
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user
		))
		self.assertEqual(response.data, expected_data, to_verbose_data(
			response_data = response.data,
			expected_data = expected_data,
			user = user
		))

	def test_creating(self):
		data: dict = {
			'title': 'Debug Post',
			'priority': Task.Priority.LOW
		}

		params = {
			'path': self.tasks_url,
			'data': data,
			'content_type': 'application/json'
		}

		last = Task.objects.last()

		response = self.client.post(**params)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(Task.objects.last(), last)

		self.client.force_login(self.user1)

		response = self.client.post(**params)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED, to_verbose_data(response.data))
		self.assertNotEqual(Task.objects.last(), last)
		self.assertEqual(Task.objects.last().created_by, self.user1)
		self.assertEqual(TaskSerializer(Task.objects.last()).data, response.data, to_verbose_data(response.data))



	def test_update_this_user_own(self):
		user = self.user1
		task = self.user1_task
		old_task = copy(task)

		assert task is not old_task

		data = {
			'title': 'Changed Title',
			'is_completed': True,

			'id': 199,
			'created_by': self.user2.pk,
		}

		params = {
			'path': self.get_task_detail_url(task.pk),
			'data': data,
			'content_type': 'application/json'
		}

		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertFalse(task.is_completed)

		self.client.force_login(user)


		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(response.data))
		self.assertEqual(response.data, TaskSerializer(task).data, to_verbose_data(response.data))
		self.assertNotEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertEqual(task.title, 'Changed Title')
		self.assertTrue(task.is_completed)
		self.assertNotEqual(task.pk, 199)
		self.assertNotEqual(task.created_by, self.user2)

	def test_update_other_user_own(self):
		user = self.user2
		task = self.user1_task
		old_task = copy(task)

		assert task is not old_task

		data = {
			'title': 'Changed Title',
			'is_completed': True,

			'id': 199,
			'created_by': self.user2.pk,
		}

		params = {
			'path': self.get_task_detail_url(task.pk),
			'data': data,
			'content_type': 'application/json'
		}

		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertFalse(task.is_completed)
		self.assertNotEqual(task.pk, 199)
		self.assertNotEqual(task.created_by, self.user2.pk)

		self.client.force_login(user)

		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, to_verbose_data(response.data))
		self.assertEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertFalse(task.is_completed)
		self.assertNotEqual(task.pk, 199)
		self.assertNotEqual(task.created_by, self.user2.pk)

	def test_update_other_user_own_witn_manager(self):
		user = self.pm_user
		task = self.user1_task
		old_task = copy(task)

		assert task is not old_task
		assert user.role == User.Role.PROJECT_MANAGER

		data = {
			'title': 'Changed Title',
			'is_completed': True,

			'id': 199,
			'created_by': self.user2.pk,
		}

		params = {
			'path': self.get_task_detail_url(task.pk),
			'data': data,
			'content_type': 'application/json'
		}

		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertFalse(task.is_completed)

		self.client.force_login(user)


		response = self.client.patch(**params)

		task.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK, to_verbose_data(response.data))
		self.assertEqual(response.data, TaskSerializer(task).data, to_verbose_data(response.data))
		self.assertNotEqual(TaskSerializer(task).data, TaskSerializer(old_task).data, to_verbose_data(response.data))
		self.assertEqual(task.title, 'Changed Title')
		self.assertTrue(task.is_completed)
		self.assertNotEqual(task.pk, 199)
		self.assertNotEqual(task.created_by, self.user2.pk)



	def test_delete_this_user_own(self):
		user = self.user2
		task = Task.objects.create(
			title = 'TASK FOR DELETE',
			created_by = self.user2
		)

		assert Task.objects.last() == task

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertEqual(Task.objects.last(), task)

		self.client.force_login(user)

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertNotEqual(Task.objects.last(), task)

	def test_delete_other_user_own(self):
		user = self.user1
		task = Task.objects.create(
			title = 'TASK FOR DELETE',
			created_by = self.user2
		)

		assert Task.objects.last() == task

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertEqual(Task.objects.last(), task)

		self.client.force_login(user)

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, to_verbose_data(response.data))
		self.assertEqual(Task.objects.last(), task)

	def test_delete_other_user_own_witn_manager(self):
		user = self.pm_user
		task = Task.objects.create(
			title = 'TASK FOR DELETE',
			created_by = self.user2
		)

		assert Task.objects.last() == task

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, to_verbose_data(response.data))
		self.assertEqual(Task.objects.last(), task)

		self.client.force_login(user)

		response = self.client.delete(self.get_task_detail_url(task.pk))

		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, to_verbose_data(response.data))
		self.assertNotEqual(Task.objects.last(), task)
