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

from tasks.tests.utils import CustomAPITestCase, to_verbose_data
from tasks.serializers import TaskSerializer, UserInfoSerializer
from tasks.models      import Task, Comment
from tasks.views       import TaskViewSet
from users.models      import User as _User # для аннотации

User: type[_User] = get_user_model()



class UserInfoSerializerTest(APITestCase):
	SECRET_FIELDS: list[str] = [
		'password',
	]

	def setUp(self):
		self.user_1 = User.objects.create(
			username = 'DebugUser 1',
			password = '1234567890$',
		)

	def test_serialized_data_doesnt_contains_secure_fields(self):
		serialized_data = UserInfoSerializer(self.user_1).data

		for secret_field in self.SECRET_FIELDS:
			self.assertNotIn(secret_field, serialized_data)



class TaskSerializerTest(CustomAPITestCase):
	COMMENTS_FIELD_NAME: str = 'comments'

	def test_many_doesnt_contains_comments_field(self):
		"""
		Проверка, что при many = True, в выходных данных нет комментариев.
		"""

		pass


	def test_not_many_contains_comments_field(self):
		"""
		Проверка, что при many = False (по умолчанию), в выходных данных\
		есть комментарии.
		"""

		pass
