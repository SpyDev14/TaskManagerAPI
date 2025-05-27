# from django.utils.translation import gettext_lazy as loc
# from django.core.exceptions   import ValidationError


# class NoInvisibleCharsAroundTheEdgesValidator:
# 	def validate(self, password: str, user = None):
# 		if password != password.strip():
# 			raise ValidationError(
# 				self.get_error_message(),
# 				"password_surrounded_by_invisible_symbols"
# 			)

# 	def get_error_message(self):
# 		return loc("The password must not begin and/or end with invisible characters.")
