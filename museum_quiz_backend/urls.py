from django.contrib import admin
from django.urls import path
from quiz import views

urlpatterns = [
    path('api/add_quiz', views.create_quiz),
    path('api/update_quiz/<str:quiz_id>', views.update_quiz),
    path('api/get_quizes/', views.get_quizes),
    path('api/get_quiz/<str:quiz_id>', views.get_quiz),
    path('api/delete_quiz/<str:quiz_id>', views.delete_quiz),
    path('api/upload_img/<str:quiz_id>', views.upload_image),
    path('api/get_img/<str:file_name>', views.get_image),
    path('api/send_answer/<str:quiz_id>', views.send_answer),
    path('api/calculate_result/<str:answer_id>', views.calculate_result),
    path('api/get_statistics/<str:quiz_id>', views.get_statistics),
]
