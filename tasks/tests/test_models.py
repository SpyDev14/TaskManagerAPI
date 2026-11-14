from django.test import TestCase
from tasks.models import Task

# Тест не очень нужен, но я его оставлю
class TaskModelTest(TestCase):
	def test_field_and_role_name_consistency(self):
		"""
		Проверка соответствтвия: `PRIORITY_CODE = ('priority_code', ...)`
		"""
		# Task.Priority - Enum, с ним можно работать так же как с Enum!!!
		for proirity_code, _ in Task.Priority.choices:
			
			self.assertTrue(hasattr(Task.Priority, proirity_code.upper()),
			   f'inconsistency priority code name: for the current name, the field should be named as "{proirity_code.upper()}"'
			)

	def test_role_name_and_verbose_role_name_consistency(self):
		"""
		Проверка соответствтвия: `... = ('priority_code', 'Priority code')`
		"""
		for role_name, role_choise_name in Task.Priority.choices:
			self.assertEqual(role_choise_name, role_name.replace('_', ' ').capitalize(),
				f'inconsistency role verbose name: verbose name must be a \'{role_name.replace('_', ' ').capitalize()}\''
			)
