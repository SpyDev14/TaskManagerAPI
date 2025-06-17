from django.contrib.auth import get_user_model
from django.contrib      import admin
from django              import forms

from users.models import User as _User
from tasks        import models

User: type[_User] = get_user_model()


# Разработчики Django очень крутые ребята, поэтому мне пришлось писать кучу кода тупо для того,
# чтобы можно было при создании указать значение в editable = False поле модели, ведь наверное
# так сложно было сделать это сразу во фреймворке. Нет, он просто не будет показывать не
# редактируемые поля и негде будет указать, что вот эти 2 поля я хочу указывать при создании.

# И, кстати, в Task мне ТОЖЕ нужно написать свою форму.
# Ну, или просто положить и пускай можно будет поменять создателя после создания задачи.
# UPD: теперь владельца task можно поменять, спасибо разработчики django, что запретили 
# работать с non-editable полями при создании новых моделей, огромное спасибо.
class CommentAdminForm(forms.ModelForm):
	created_by_on_create = forms.ModelChoiceField(label = 'Created by', queryset = User.objects.all())
	task_on_create       = forms.ModelChoiceField(label = 'Task', queryset = models.Task.objects.all())

	class Meta:
		model = models.Comment
		fields = '__all__'


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Устанавливаем текущего пользователя по умолчанию
		if not self.instance.pk and 'created_by_on_create' in self.fields:
			self.fields['created_by_on_create'].initial = self.current_user # устанавливаем в get_form

	def save(self, commit: bool = True):
		if not self.instance.pk:
			self.instance.created_by = self.cleaned_data['created_by_on_create']
			self.instance.task       = self.cleaned_data['task_on_create']

		return super().save(commit)


class CommentAdmin(admin.ModelAdmin):
	form = CommentAdminForm

	def get_form(self, request, *args, **kwargs):
		# Передаем текущего пользователя в форму
		form = super().get_form(request, *args, **kwargs)
		form.current_user = request.user # других способов нет
		return form

	def get_readonly_fields(self, request, obj=None):
		if obj:
			return ('created_by', 'task')
		return ()

	def get_fields(self, request, obj=None):
		if obj:
			return ['content', 'created_by', 'task']
		return ['content', 'created_by_on_create', 'task_on_create']


admin.site.register(models.Comment, CommentAdmin)
admin.site.register((
	models.Task,
))
