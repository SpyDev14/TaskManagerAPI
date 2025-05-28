from django.test import TestCase
from tasks.models import Task


class TaskModelTest(TestCase):
	def test_field_and_role_name_consistency(self):
		"""
		Проверка соответствтвия: `PRIORITY_CODE = ('priority_code', ...)`
		"""
		for proirity_code, _ in Task.Priority.choices:
			self.assertTrue(hasattr(Task.Priority, proirity_code.upper()),
			   f'inconsistency priority code name: for the current name, the field should be named as "{proirity_code.upper()}"'
			)

	def test_role_name_and_verbose_role_name_consistency(self):
		"""
		Проверка соответствтвия: `... = ('priority_code', 'Priority Code')`
		"""
		for role_name, role_choise_name in Task.Priority.choices:
			self.assertEqual(role_choise_name, role_name.replace('_', ' ').title(),
				f'inconsistency role verbose name: verbose name must be a \'{role_name.replace('_', ' ').title()}\''
			)



class CommentModelTest(TestCase):
	def test_plug(self):
		print('\n\033[33mCommentModelTest not implemented!\033[0m')
