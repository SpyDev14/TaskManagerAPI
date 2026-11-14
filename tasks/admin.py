from django.contrib.auth import get_user_model
from django.contrib      import admin
from django.db.models    import QuerySet
from django              import forms

from users.models import User as _User
from tasks        import models

User: type[_User] = get_user_model()


# Спасибо, разработчики django, что вы запланировали editable = False поля как сугубо-технические
# и мне пришлось писать свою кастомную форму для админки, чтобы иметь возможность создавать задачи.
class CommentAdminForm(forms.ModelForm):
	created_by_on_create = forms.ModelChoiceField(
		label = 'Created by',
		required = False,
		queryset = User.objects.all()
	)
	task_on_create = forms.ModelChoiceField(
		label = 'Task',
		required = False,
		queryset = models.Task.objects.all()
	)

	class Meta:
		model = models.Comment
		fields = '__all__'


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Устанавливаем текущего пользователя по умолчанию
		if not self.instance.pk and 'created_by_on_create' in self.fields:
			self.fields['created_by_on_create'].required = True
			self.fields['task_on_create'].required = True

			# устанавливаем в get_form
			if hasattr(self, 'current_user'):
				self.fields['created_by_on_create'].initial = self.current_user

	def save(self, commit: bool = True):
		if not self.instance.pk:
			self.instance.created_by = self.cleaned_data['created_by_on_create']
			self.instance.task       = self.cleaned_data['task_on_create']

		return super().save(commit)


class CommentAdmin(admin.ModelAdmin):
	form = CommentAdminForm
	list_display = ['id', 'task', 'created_by', 'short_content', 'created_at']
	list_filter = ['task', 'created_by']
	list_display_links = ['id']
	search_fields = ['content', 'task__title', 'created_by__username']
	ordering = ['task', 'created_at']

	def short_content(self, obj: models.Comment):
		MAX_LENGTH: int = 48

		if len(obj.content) > MAX_LENGTH:
			return str(obj.content[:MAX_LENGTH]) + '...'
		return str(obj.content)
	short_content.short_description = 'Content'

	def get_form(self, request, *args, **kwargs):
		# Передаем текущего пользователя в форму
		form = super().get_form(request, *args, **kwargs)
		form.current_user = request.user # других способов нет
		return form

	def get_readonly_fields(self, request, obj=None):
		if obj:
			return ['created_by', 'task']
		return ()

	def get_fields(self, request, obj=None):
		if obj:
			return ['content', 'created_by', 'task']
		return ['content', 'created_by_on_create', 'task_on_create']


class TaskAdmin(admin.ModelAdmin):
	list_display = [
		'id', 'title', 'created_by', 'assigned_to',
		'due_date', 'priority', 'is_completed', #'created_at'
	]
	list_display_links = ['title']
	search_fields = ['title', 'description', 'created_by__username']
	# ordering = ['id']
	list_filter = ['priority', 'created_by', 'assigned_to']
	list_per_page = 50

	actions = ['mark_as_completed', 'mark_as_uncompleted']

	def mark_as_completed(self, request, queryset: QuerySet):
		queryset.update(is_completed = True)
	mark_as_completed.short_description = "Отметить выполненными"

	def mark_as_uncompleted(self, request, queryset: QuerySet):
		queryset.update(is_completed = False)
	mark_as_uncompleted.short_description = "Отметить невыполненными"

admin.site.register(models.Comment, CommentAdmin)
admin.site.register(models.Task, TaskAdmin)
