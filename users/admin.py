from django.contrib.auth.admin import UserAdmin
from django.contrib.auth       import get_user_model
from django.utils.translation  import gettext_lazy as loc
from django.contrib            import admin

from users.models import User as _User # для аннотации
from users        import models

User: type[_User] = get_user_model()


class CustomUserAdmin(UserAdmin):
	list_display = ('id', ) + UserAdmin.list_display + ('get_role_display',)
	list_display_links = ['username']
	ordering = ['id']

	fieldsets = UserAdmin.fieldsets + (
		(loc('Роль пользователя'), {'fields': ('role',)}),
	)

	add_fieldsets = UserAdmin.add_fieldsets + (
        (loc('Роль пользователя'), {'fields': ('role',)}),
    )

	def get_role_display(self, obj: _User):
		return obj.get_role_display()
	get_role_display.short_description = loc('Роль')


admin.site.register(User, CustomUserAdmin)
