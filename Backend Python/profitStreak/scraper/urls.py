from django.urls import path
from .views import process_query

urlpatterns = [
    path('processQuery/', process_query, name='processQuery'),
]
