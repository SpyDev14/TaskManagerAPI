from django.test  import TestCase
from tasks.models import User



class UserModelTest(TestCase):
	def test_role_names_consistency(self):
		# тут должна была быть проверка на соответствие значений и названия роли :(
		#   - проверка: ROLE_NAME = ('role_name', 'Role Name')
		# сейчас это какой-то очень странный тест, возможно потом удалю
		for role_name, role_choise_name in User.Role.choices:
			self.assertEqual(role_name.replace('_', ' ').title(), role_choise_name)