from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.db import models


class User(AbstractUser):
	class Role(models.TextChoices):
		REGULAR_USER    = ('regular_user',    'Regular User')
		PROJECT_MANAGER = ('project_manager', 'Project Manager')


	role = models.CharField(
		max_length = 32,
		choices = Role.choices,
		default = Role.REGULAR_USER
	)
	# сейчас это поле уже практически не нужно
	email = models.EmailField(null = True, blank = True)


	def __str__(self) -> str:
		return self.username
	
	# MARK: какая-то мутная тема
	def save(self, *args, **kwargs):
		is_creating = not self.pk
		password_changed = self._password is None

		print(password_changed)

		if is_creating or password_changed:
			self.set_password(self.password)

		super().save(*args, **kwargs)