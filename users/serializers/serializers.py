from django.contrib.auth.password_validation import validate_password
from django.contrib.auth                     import get_user_model
from rest_framework_simplejwt.serializers    import TokenRefreshSerializer
from rest_framework                          import serializers

from users.serializers.fields import CookieSourceCharField
from users.models             import User as _User # для аннотации
from users                    import local_settings

__all__ = [
	'UserRegisterSerializer',
	'CookieTokenRefreshSerializer'
]

User: type[_User] = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
	password = serializers.CharField(
		write_only = True,
		validators = [validate_password],
		style = {'input_type': 'password'} # для браузеров, чтобы инпуты были стиля пароля по умолчанию
	)

	class Meta:
		model = User
		fields = (
			'username',
			'password',
			'email',
			'role',
		)
		extra_kwargs = {
			'role': { 'read_only': True }
		}

	def create(self, validated_data):
		serializers.raise_errors_on_nested_writes('create', self, validated_data)

		return self.Meta.model.objects.create_user(**validated_data)


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
	refresh = CookieSourceCharField(
		target_key = local_settings.REFRESH_TOKEN_COOKIE_NAME,
		write_only = True
	)

	access = None
