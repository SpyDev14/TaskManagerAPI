from rest_framework.filters import OrderingFilter


class TaskOrderingFilter(OrderingFilter):
	DUE_DATE_FIELD_NAME: str = 'due_date'
	IS_COMPLETED_FIELD_NAME: str = 'is_completed'
	

	def get_ordering(self, request, queryset, view):
		ordering = super().get_ordering(request, queryset, view)

		if not ordering: return ordering

		if any(order_param.lstrip('-') == self.DUE_DATE_FIELD_NAME for order_param in ordering):
			ordering = (self.IS_COMPLETED_FIELD_NAME, *ordering)

		return ordering
