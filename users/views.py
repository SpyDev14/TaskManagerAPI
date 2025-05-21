from django.contrib.auth             import authenticate
from django.conf                     import settings
from django.http.request             import HttpRequest
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.views  import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions      import IsAuthenticated
from rest_framework.response         import Response
from rest_framework.request          import Request
from rest_framework                  import generics, status, views

from .serializers import UserLoginSerializer, UserRegisterSerializer
from .models import User
from . import settings as local_settings


# В аргументы всех View всегда передаётся объект Request из DRF, а там
# где в аннотации указанно HttpRequest из django - это сделанно для
# правильной работы аннотации IDE (которая почему-то не знает,
# что DRF:Request <- DJANGO:HttpRequest)

# Работает по ссылке так как Responce - ссылочный объект
def _add_access_token_to_response_cookies_from_str(
	response: Response,
	access_token: str
) -> None:
	response.set_cookie(
		key = local_settings.ACCESS_TOKEN_COOKIE_NAME,
		value = access_token,
		max_age = AccessToken.lifetime,
		**local_settings.TOKEN_COOKIE_PARAMS
	)

	
def _add_tokens_to_response_cookies_from_raw_tokens(
		response: Response,
		refresh_token: str,
		access_token: str
	) -> None:

	_add_access_token_to_response_cookies_from_str(response, access_token)

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
	permission_classes = []

	def create(self, request: Request, *args, **kwargs):
		# Иначе аннотация не работает, IDE сошла с ума, к сожалению
		def get_serializer(*, data) -> UserRegisterSerializer:
			return self.get_serializer(data = data)
		
		serializer = get_serializer(data = request.data)
		serializer.is_valid(raise_exception = True)

		user: User = serializer.save()

		refresh = RefreshToken.for_user(user)

		headers = self.get_success_headers(serializer.data)

		response = Response(
			serializer.data,
			status = status.HTTP_201_CREATED,
			headers = headers
		)

		_add_tokens_to_response_cookies(response, refresh)

		return response


class LoginView(generics.GenericAPIView):
	serializer_class = UserLoginSerializer
	permission_classes = []

	def post(self, request: Request):
		# Иначе аннотация не работает, IDE сумасшедшая дура, к сожалению
		def get_serializer(*, data) -> UserLoginSerializer:
			return self.get_serializer(data = data)
		
		serializer = get_serializer(data = request.data)
		serializer.is_valid(raise_exception = True)

		user: User | None = authenticate(
			request,
			username = serializer.validated_data['username'],
			password = serializer.validated_data['password'],
		)
		
		if not user:
			return Response(
				{'detail': 'Invalid credentials'},
				status = status.HTTP_401_UNAUTHORIZED
			)

		refresh = RefreshToken.for_user(user)
			
		response = Response()
		
		_add_tokens_to_response_cookies(response, refresh)

		return response


class LogoutView(views.APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request: Request):
		user: User = request.user

		refresh = RefreshToken.for_user(user)

		refresh.blacklist()

		response = Response()
		response.delete_cookie(key = local_settings.ACCESS_TOKEN_COOKIE_NAME)
		response.delete_cookie(key = local_settings.REFRESH_TOKEN_COOKIE_NAME)

		return response
	

# MARK: JWT Token Views
class CookieTokenObtainPairView(TokenObtainPairView):
	def post(self, request: HttpRequest):
		response = super().post(request)

		if not response.status_code == status.HTTP_200_OK:
			return response
		
		
		raw_access_token  = response.data['access']
		raw_refresh_token = response.data['refresh']

		_add_tokens_to_response_cookies_from_raw_tokens(
			response = response,
			access_token  = raw_access_token,
			refresh_token = raw_refresh_token,
		)

		del response.data['access']
		del response.data['refresh']

		return response
	

class CookieTokenRefreshView(TokenRefreshView):
	def post(self, request: HttpRequest):
		raw_refresh_token: str = request.COOKIES.get(local_settings.REFRESH_TOKEN_COOKIE_NAME)

		if raw_refresh_token:
			request.data['refresh'] = raw_refresh_token

		response = super().post(request)

		if not response.status_code == status.HTTP_200_OK:
			return response
		

		access_token = response.data['access']
		_add_access_token_to_response_cookies_from_str(response, access_token)

		del response.data['access']

		return response