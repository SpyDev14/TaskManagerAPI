from rest_framework.request import Request
from django.contrib.auth    import signals, get_user_model
from django.dispatch        import receiver
from django.utils           import timezone

from users.models import User as _User # Для аннотации
User: type[_User] = get_user_model()

# @receiver(signals.user_logged_in)
# def update_user_last_login_data(sender, request: Request, user: _User):
# 	user.last_login = timezone.now()
# 	user.save(update_fields = ['last_login'])
