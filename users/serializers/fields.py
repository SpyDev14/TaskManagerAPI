from django.utils.translation import gettext_lazy as loc
from django.http.request      import HttpRequest
from rest_framework.request   import Request
from rest_framework.fields    import empty
from rest_framework           import serializers


class CookieSourceCharField(serializers.CharField):
	"""
	Берёт поле не из data, а из COOKIES request объекта.<br>
	В контексте ожидает объект запроса по ключу `request`
	"""
	default_error_messages = {
		'required': 'Value is required in cookies with key: {target_key}'
	}

	def __init__(self, *, target_key: str, **kwargs):
		if not target_key:
			raise ValueError('target_key cannot be empty.')
		self.target_key = target_key
		super().__init__(**kwargs)


	def run_validation(self, data = empty):
		request: Request | HttpRequest = self.context.get('request')
		if not request:
			raise serializers.ValidationError('Request object is missing in context.')

		cookie_value = request.COOKIES.get(self.target_key)
		if not cookie_value and self.required:
			self.fail(
				'required',
				target_key = f'`{self.target_key}`'
			)
		
		return super().run_validation(cookie_value)