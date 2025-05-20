from rest_framework              import serializers
from django.contrib.auth.hashers import make_password

from .models import User

class UserRegisterSerializer(serializers.ModelSerializer):
	password = serializers.CharField(write_only = True)

	class Meta:
		model = User
		fields = (
			'username',
			'password',
			'email',
			'role',
		)
		extra_kwargs = {
			'email': { 'required': False },
			'role':  { 'required': False },
		}

	def create(self, validated_data):
		validated_data['password'] = make_password(validated_data['password'])
		return super().create(validated_data)
	

class UserLoginSerializer(serializers.Serializer):
	username = serializers.CharField()
	password = serializers.CharField(write_only = True)

	