from django.urls import path, include
from rest_framework.routers        import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from tasks import views


task_router = DefaultRouter()
task_router.register('tasks', views.TaskViewSet, basename = 'tasks')

task_comments_router = NestedDefaultRouter(
	parent_router = task_router,
	parent_prefix = 'tasks',
	lookup = 'task'
)
task_comments_router.register('comments', views.CommentViewSet, basename = 'task-comments')

urlpatterns = [
	path('api/', include([
		*task_router.urls,
		*task_comments_router.urls,
	])),
]
