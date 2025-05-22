from django.test  import TestCase
from users.models import User



class UserModelTest(TestCase):
	def test_field_and_role_name_consistency(self):
		"""
		Проверка соответствтвия: `ROLE_NAME = ('role_name', ...)`
		"""
		for role_name, role_choise_name in User.Role.choices:
			self.assertTrue(hasattr(User.Role, role_name.upper()),
			   f'inconsistency role name: for the current name, the field should be named as "{role_name.upper()}"'
			)

	def test_role_name_and_verbose_role_name_consistency(self):
		"""
		Проверка соответствтвия: `... = ('role_name', 'Role Name')`
		"""
		for role_name, role_choise_name in User.Role.choices:
			self.assertEqual(role_choise_name, role_name.replace('_', ' ').title(),
				f'inconsistency role verbose name: verbose name must be a \'{role_name.replace('_', ' ').title()}\''
			)


	def test_password_hasing_on_creating(self):
		user_wrong = User.objects.create(
			username = 'StupidOleg',
			password = '12345'
		)

		self.assertEqual(user_wrong.password, '12345')

		user = User.objects.create_user(
			username = 'Oleg',
			password = '12345'
		)

		self.assertNotEqual(user.password, '12345')