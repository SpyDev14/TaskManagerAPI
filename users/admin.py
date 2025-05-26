from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as loc
from django.contrib            import admin

from users import models


class CustomUserAdmin(UserAdmin):
	list_display = ('id',) + UserAdmin.list_display + ('get_role_display',)
	list_display_links = ('id',) + UserAdmin.list_display_links
	
	fieldsets = UserAdmin.fieldsets + (
		(loc('Роль пользователя'), {'fields': ('role',)}),
	)

	add_fieldsets = UserAdmin.add_fieldsets + (
        (loc('Роль пользователя'), {'fields': ('role',)}),
    )

	def get_role_display(self, obj: models.User):
		return obj.get_role_display()
	get_role_display.short_description = loc('Роль')


admin.site.register(models.User, CustomUserAdmin)