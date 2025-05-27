from django.contrib.auth.hashers import make_password
from django.contrib.auth         import get_user_model
from django.test                 import TestCase

from users.serializers import UserRegisterSerializer
from users.models      import User as _User # для аннотации

User: type[_User] = get_user_model()


class UserSerializersTest(TestCase):
	def test_register_serializer_serializaation(self):
		user = User.objects.create_user(
			username = 'Olegos123',
			password = 'debugpass',
			role = User.Role.PROJECT_MANAGER
		)

		data = UserRegisterSerializer(user).data

		expected_data = {
			'username': 'Olegos123',
			'email': '',
			'role': str(User.Role.PROJECT_MANAGER)
		}

		self.assertEqual(data, expected_data)


	def test_register_serializer_validation(self):
		data = {
			'username': 'Olegos123',
			'role': str(User.Role.PROJECT_MANAGER)
		}

		serializer = UserRegisterSerializer(data = data)
		self.assertFalse(serializer.is_valid())

		data = {
			'username': 'Olegos123',
			'password': 'debugpass',
			'role': str(User.Role.PROJECT_MANAGER)
		}

		serializer = UserRegisterSerializer(data = data)
		self.assertTrue(serializer.is_valid())

		user: _User = serializer.save()
		self.assertEqual(user.role, User.Role.REGULAR_USER)
