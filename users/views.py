from django.contrib.auth             import authenticate
from django.conf                     import settings
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.response         import Response
from rest_framework.request          import Request
from rest_framework                  import generics, status

from .serializers import UserLoginSerializer, UserRegisterSerializer
from .models import User


def _add_tokens_to_responce_cookies(response: Response, refresh: RefreshToken) -> None:
	response.set_cookie(
		key = AccessToken.token_type,
		value = str(refresh.access_token),
		httponly = True,
		secure = True,
		max_age = AccessToken.lifetime
	)

	response.set_cookie(
		key = RefreshToken.token_type,
		value = str(refresh),
		httponly = True,
		secure = True,
		max_age = RefreshToken.lifetime
	)


class RegisterView(generics.CreateAPIView):
	queryset = User.objects.all()
	serializer_class = UserRegisterSerializer
	permission_classes = []

	def create(self, request: Request, *args, **kwargs):
		# Иначе аннотация не работает, IDE сумасшедшая дура, к сожалению
		def get_serializer(*, data) -> UserLoginSerializer:
			return self.get_serializer(data = data)
		
		serializer = get_serializer(data = request.data)
		serializer.is_valid(raise_exception = True)

		user: User = serializer.save()

		refresh = RefreshToken.for_user(user)
		
		# refresh.payload.update({
		# 	'user_id':  user.pk,
		# 	'username': user.username,
		# })

		headers = self.get_success_headers(serializer.data)

		response = Response(
			serializer.data,
			status = status.HTTP_201_CREATED,
			headers = headers
		)

		_add_tokens_to_responce_cookies(response, refresh)

		return response

class LoginView(generics.GenericAPIView):
	serializer_class = UserLoginSerializer
	permission_classes = []

	def post(self, request):
		# Просто иначе аннотация не работает, IDE сумасшедшая дура
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
				{'error': 'Invalid credentials'},
				status = status.HTTP_401_UNAUTHORIZED
			)

		refresh = RefreshToken.for_user(user)
			
		response = Response()
		
		_add_tokens_to_responce_cookies(response, refresh)

		return response