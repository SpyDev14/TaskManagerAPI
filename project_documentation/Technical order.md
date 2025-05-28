## Тестовое задание: Task Manager API
#### Требования
- Без `темплейтов`, только API. ✅
- JWT-аутентификация (через `djangorestframework-simplejwt`). ✅
- Статика и медиа доступны через API root. ✅

#### Эндпоинты:
- **Задачи**
	- `api/tasks/`: `[GET, POST]`
	- `api/tasks/<pk>/`: `[GET, PUT, PATCH, DELETE]`
	- `api/tasks/<pk>/comments/`: `[GET, POST]`
	- `api/tasks/<pk>/comments/<pk>/`: `[GET, PUT, PATCH, DELETE]`
- **Авторизация**
	- `api/token/`: `[POST]` `{username, password}`
	- `api/token/refresh/`: `[POST]` `{refresh (в cookies)}`
	- `api/register/`: `[POST]` `{username, password + поля User}`
	- `api/logout/`: `[POST]`
#### Роли пользователей
- **Regular User**
	- Видит только свои задачи
	- Изменяет только свои задачи✅
	- Может оставлять комментарии только под своими задачами
	- Может удалять только свои комментарии
	- Будучи назначенным на задачу имеет такие же права, как и создатель

- **Project Manager**
	- Видит все задачи✅
	- Изменяет все задачи✅
	- Может оставлять комментарии под всеми задачами
	- Может назначать людей на задачи
	- Может удалять только свои комментарии

Роль хранится в модели пользователя или под роль создать отдельную модель.  ✅

#### Функционал API
- Регистрация и логин через API (выдача JWT). ✅
- **CRUD для задач**
	- В соответствии с ролями
- **CRUD для комментариев**
	- В соответствии с ролями
- **`GET /api/tasks/`**
	- **Фильтры** (`==`): по `priority`, `assigned_to`, `is_completed`.
	- **Сортировка** (по полям): по `due_date`, `created_at`.
	- **Поиск** (текст): по `title`, `description`.

#### Модель задачи:
- `title`
- `description`
- `is_completed`
- `created_at`
- `attachment (файл)`
- `created_by`
- `due_date`
- `priority (low, medium, high)
- `assigned_to (кто назначен)`
#### Модель комментария:
- `task`
- `author`
- `content`
- `created_at`
#### API root (/api/) ✅
возвращает ссылки на основные эндпоинты и на статику/медиа
![[Pasted image 20250519120906.png]]