from django.utils.translation            import gettext_lazy as loc
from django.contrib.auth                 import authenticate, get_user_model
from django.http.request                 import HttpRequest
from django.utils                        import timezone
from django.conf                         import settings
from rest_framework.permissions          import IsAuthenticatedOrReadOnly
from rest_framework.response             import Response
from rest_framework.request              import Request
from rest_framework                      import generics, status, views
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens     import RefreshToken, AccessToken
from rest_framework_simplejwt.views      import TokenObtainPairView, TokenRefreshView

from users.serializers import UserRegisterSerializer, CookieTokenRefreshSerializer
from users.permissinos import IsAnonymousOrReadOnly
from users.models      import User as _User # Для аннотации
from users             import local_settings

User: type[_User] = get_user_model()

# В аргументы всех View всегда передаётся объект Request из DRF,
# но в аннотации везде указанно `Request (из DRF) | HttpRequest (из django)`
# для правильной работы аннотации IDE, которая почему-то не знает,
# что DRF:Request наследуется от DJANGO:HttpRequest из-за чего
# (по крайней мере, у меня в VSCode) оно не знает, что
# у DRF:Request есть поля и методы HttpRequest
# и помечает их как Any и мол вообще, что это такое

# Работает по ссылке так как Responce - ссылочный объект
def _add_tokens_to_response_cookies_from_raw_tokens(
		response: Response,
		refresh_token: str,
		access_token: str
	) -> None:

	response.set_cookie(
		key = local_settings.ACCESS_TOKEN_COOKIE_NAME,
		value = access_token,
		max_age = AccessToken.lifetime,
		**local_settings.TOKEN_COOKIE_PARAMS
	)

	response.set_cookie(
		key = local_settings.REFRESH_TOKEN_COOKIE_NAME,
		value = refresh_token,
		max_age = RefreshToken.lifetime,
		**local_settings.TOKEN_COOKIE_PARAMS
	)


def _add_tokens_to_response_cookies(response: Response, refresh: RefreshToken) -> None:
	_add_tokens_to_response_cookies_from_raw_tokens(
		response = response,
		refresh_token = str(refresh),
		access_token  = str(refresh.access_token)
	)


class RegisterView(generics.CreateAPIView):
	queryset = User.objects.all()
	serializer_class = UserRegisterSerializer
	permission_classes = [IsAnonymousOrReadOnly]


	# Для работы аннотации в глупой IDE          ∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨∨
	def get_serializer(self, *args, **kwargs) -> UserRegisterSerializer:
		return super().get_serializer(*args, **kwargs)

	def create(self, request: Request | HttpRequest, *args, **kwargs):
		serializer = self.get_serializer(data = request.data)
		serializer.is_valid(raise_exception = True)

		user: _User = serializer.save()

		refresh = RefreshToken.for_user(user)

		headers = self.get_success_headers(serializer.data)

		response = Response(
			serializer.data,
			status = status.HTTP_201_CREATED,
			headers = headers
		)

		_add_tokens_to_response_cookies(response, refresh)

		return response


class LogoutView(views.APIView):
	# description = \
	# 	f"It waits for `{local_settings.ACCESS_TOKEN_COOKIE_NAME}`"\
	# 	f" and `{local_settings.REFRESH_TOKEN_COOKIE_NAME}` in cookies,"\
	# 		" and then deletes them from cookies in response and"\
	# 		" blacklists them on the server. Does not return body."

	permission_classes = [IsAuthenticatedOrReadOnly]

	def post(self, request: Request | HttpRequest):
		user: _User = request.user

		refresh = RefreshToken.for_user(user)

		refresh.blacklist()

		response = Response()
		response.delete_cookie(key = local_settings.ACCESS_TOKEN_COOKIE_NAME)
		response.delete_cookie(key = local_settings.REFRESH_TOKEN_COOKIE_NAME)

		return response


# MARK: JWT-Token Views
class CookieTokenObtainPairView(TokenObtainPairView):
	def post(self, request: Request | HttpRequest):

		# При ошибке вызывает исключение
		response = super().post(request)

		raw_access_token  = response.data['access']
		raw_refresh_token = response.data['refresh']
		

		_add_tokens_to_response_cookies_from_raw_tokens(
			response = response,
			access_token  = raw_access_token,
			refresh_token = raw_refresh_token,
		)

		# дупликация кода (дубликат в TokenRefresh)
		# лучше сигналы
		user_id = AccessToken(raw_access_token)['user_id']
		user = User.objects.get(pk = user_id)
		user.last_login = timezone.now()
		user.save(update_fields = ['last_login'])

		response.data = None
		return response


class CookieTokenRefreshView(TokenRefreshView):
	description = \
		f"Waits for `refresh` in the `{local_settings.REFRESH_TOKEN_COOKIE_NAME}` cookie and," \
		f" on success, sets a new `{local_settings.ACCESS_TOKEN_COOKIE_NAME}`" \
		f" and `{local_settings.REFRESH_TOKEN_COOKIE_NAME}`" \
		 " in the HttpOnly, Secure, this only SameSite, cookies." \
		 " Does not return body"

	# Для работы аннотации в глупой IDE и добавляет пустую data
	def get_serializer(self, *args, **kwargs) -> CookieTokenRefreshSerializer:
		return super().get_serializer(data = {}, *args, **kwargs)

	def post(self, request: Request | HttpRequest):
		# Request по умолчанию идёт в context
		# от куда он берёт cookie из которых он уже
		# берёт refresh_token
		serializer = self.get_serializer()

		# < Скопировано из super().post() >
		try:
			serializer.is_valid(raise_exception = True)
		except TokenError as e:
			raise InvalidToken(e.args[0])
		# </>

		response = Response(status = status.HTTP_200_OK)

		_add_tokens_to_response_cookies_from_raw_tokens(
			response = response,
			access_token = serializer.validated_data['access'],
			refresh_token = serializer.validated_data['refresh'],
		)

		# дупликация кода (дубликат в TokenObtain)
		# лучше сигналы
		user_id = AccessToken(serializer.validated_data['access'])['user_id']
		user = User.objects.get(pk = user_id)
		user.last_login = timezone.now()
		user.save(update_fields = ['last_login'])

		assert response.data is None, str(response.data)

		return response
