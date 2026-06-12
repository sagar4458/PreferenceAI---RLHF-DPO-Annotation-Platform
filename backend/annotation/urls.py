from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/me/', views.me, name='me'),
    path('api/next-task/', views.next_task, name='next_task'),
    path('api/submit-annotation/', views.submit_annotation, name='submit_annotation'),
    path('api/agreement/<int:task_id>/', views.agreement_view, name='agreement'),
    path('api/export/', views.export_view, name='export'),
    path('api/create-task/', views.create_task, name='create_task'),
    path('api/import-csv/', views.import_csv, name='import_csv'),
    path('api/stats/', views.stats, name='stats'),
    path('', views.home, name='home'),
    path('api/csrf/', views.csrf_token, name='csrf'),
]