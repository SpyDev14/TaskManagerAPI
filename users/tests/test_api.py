from copy import copy
import json

from django.utils.translation import gettext_lazy as loc
from django.contrib.auth      import get_user_model
from django.http.response     import HttpResponse
from django.urls              import reverse
from rest_framework.response  import Response
from rest_framework.test      import APITestCase
from rest_framework           import status

from users.tests.debug_client import CookieJWTDebugClient
from users.models             import User as _User # для аннотации
from users                    import local_settings as _settings

User: type[_User] = get_user_model()


import json
def to_verbose_data(data) -> str:
	if not data:
		return '>Data is None'


class UserAPITest(APITestCase):
	client_class = CookieJWTDebugClient

	def setUp(self):
		self.user_password = 'HoleraFredyFazbear'
		self.user = User.objects.create_user(
			username = 'FredyFasbear',
			password = self.user_password,
			email = 'fredyfazbear@gmail.com',
			role = str(User.Role.PROJECT_MANAGER)
		)
		self.user2 = User.objects.create(
			username = 'ValeryOlegov',
			password = self.user.password
		)

		self.register_url      = reverse('register')
		self.token_pair_url    = reverse('token-obtain_pair')
		self.token_refresh_url = reverse('token-refresh')
		self.logout_url        = reverse('logout')


	def test_options_all(self):
		response = self.client.options(self.logout_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.register_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.token_pair_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.token_refresh_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)


		self.client.force_login(self.user)


		response = self.client.options(self.logout_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.register_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.token_pair_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.options(self.token_refresh_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)


	def test_register(self):
		last_user = User.objects.last()

		# такой пользователь уже есть
		response = self.client.post(
			self.register_url,
			{
				'username': 'FredyFasbear',
				'password': 'HelloWorld12345',
				'role': str(User.Role.PROJECT_MANAGER)
			},
			content_type = 'application/json'
		)

		expected_response_data = {
			"username": [
				"Пользователь с таким именем уже существует."
			]
		}

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(User.objects.last(), last_user)
		self.assertEqual(response.data, expected_response_data)


		# такого пользователя нет, но пользователь ввёл плохой пароль
		response = self.client.post(
			self.register_url,
			{
				'username': 'FredyFasbearLLC',
				'password': '1',
				'role': str(User.Role.PROJECT_MANAGER)
			},
			content_type = 'application/json'
		)

		expected_response_data = {
			"password": [
				"This password is too short. It must contain at least 8 characters.", # странно
				"Введённый пароль слишком широко распространён.",
				"Введённый пароль состоит только из цифр."
			]
		}

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(User.objects.last(), last_user)
		self.assertEqual(response.data, expected_response_data)


		# такого пользователя нет, пароль нормальный, запись создаётся
		response = self.client.post(
			self.register_url,
			{
				'username': 'FredyFasbearLLC',
				'password': 'HelloWorld12345$',
				'role': str(User.Role.PROJECT_MANAGER)
			},
			content_type = 'application/json'
		)

		expected_response_data = {
			'username': 'FredyFasbearLLC',
			'email': '',
			'role': str(User.Role.REGULAR_USER)
		}

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(User.objects.last().username, 'FredyFasbearLLC')
		self.assertEqual(response.data, expected_response_data)


		# пользователь под своей учётной записью регистрируется (зачем? поэтому 403, только анонимы)
		response = self.client.post(
			self.register_url,
			{
				'username': 'FredyFasbearLLC2',
				'password': 'HelloWorld',
				'role': str(User.Role.PROJECT_MANAGER)
			},
			content_type = 'application/json'
		)

		expected_response_data = {
			'username': 'FredyFasbearLLC2',
			'email': '',
			'role': str(User.Role.REGULAR_USER)
		}

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(User.objects.last().username, 'FredyFasbearLLC')

	def test_login(self):
		# вход анонима в уч запись с неправильным паролем
		response = self.client.post(
			self.token_pair_url,
			{
				'username': self.user.username,
				'password': 'WRONG'
			},
			content_type = 'application/json'
		)

		expected_data = {
			'detail': 'Не найдено активной учетной записи с указанными данными'
		}

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(response.data, expected_data)
		self.assertNotIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


		# вход анонима в уч запись
		response = self.client.post(
			self.token_pair_url,
			{
				'username': self.user.username,
				'password': self.user_password
			},
			content_type = 'application/json'
		)


		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsNone(response.data)
		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


		# вход авторизованого в другую уч. запись с неправильным паролем
		old_access  = self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME]
		old_refresh = self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME]
		response = self.client.post(
			self.token_pair_url,
			{
				'username': self.user2.username,
				'password': 'WRONG'
			},
			content_type = 'application/json'
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(response.data, expected_data)
		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertEqual(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME], old_access)
		self.assertEqual(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME], old_refresh)


		# вход авторизованного в другую уч. запись
		response = self.client.post(
			self.token_pair_url,
			{
				'username': self.user.username,
				'password': self.user_password
			},
			content_type = 'application/json'
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsNone(response.data)
		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotEqual(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME], old_access)
		self.assertNotEqual(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME], old_refresh)

	# нужна проверка, если токен неправильный
	def test_refresh_token(self):
		# аноним без токенов рефрешит
		expected_data_on_nothing_in_request = {
			"refresh": [
				f"Value is required in cookies with key: `{_settings.REFRESH_TOKEN_COOKIE_NAME}`"
			]
		}

		response: Response = self.client.post(self.token_refresh_url)
		# старые токены должны появится в blacklist

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(json.dumps(response.data), json.dumps(expected_data_on_nothing_in_request),
			json.dumps(response.data, indent = 4))
		self.assertNotIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


		self.client.force_login(self.user)

		old_access:  str = self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME]
		old_refresh: str = self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME]

		# авторизованный с access & refresh в куках
		response = self.client.post(self.token_refresh_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsNone(response.data)
		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotEqual(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME], old_access)
		self.assertNotEqual(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME], old_refresh)


		# авторизованный с access & refresh в куках повторно
		response = self.client.post(self.token_refresh_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsNone(response.data)
		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotEqual(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME], old_access)
		self.assertNotEqual(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME], old_refresh)


		# авторизованный передаёт refresh через body
		old_access  = self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME]

		refresh_token = self.client.cookies.pop(_settings.REFRESH_TOKEN_COOKIE_NAME)

		data = { 'refresh': refresh_token }
		response = self.client.post(self.token_refresh_url, data = data, content_type = 'application/json')

		# expected data такая же, как и если бы мы ничего не "передали"
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data, expected_data_on_nothing_in_request)
		self.assertEqual(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME], old_access)
		self.assertNotIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


	def test_logout(self):
		response = self.client.post(self.logout_url)

		expected_data = {
			"detail": "Учетные данные не были предоставлены."
		}

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(response.data, expected_data)
		self.assertNotIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertNotIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


		self.client.force_login(self.user)

		self.assertIn(_settings.ACCESS_TOKEN_COOKIE_NAME, self.client.cookies)
		self.assertIn(_settings.REFRESH_TOKEN_COOKIE_NAME, self.client.cookies)


		response = self.client.post(self.logout_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		# этот клиент немного двинутый, ибо он не удаляет куки с истёкшим сроком действия
		# как это сделал бы браузер, так что проверяем на пустоту
		self.assertFalse(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME].value)
		self.assertFalse(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME].value)

		response = self.client.post(self.logout_url)
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertFalse(self.client.cookies[_settings.ACCESS_TOKEN_COOKIE_NAME].value)
		self.assertFalse(self.client.cookies[_settings.REFRESH_TOKEN_COOKIE_NAME].value)
