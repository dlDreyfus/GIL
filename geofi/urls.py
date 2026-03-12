from django.urls import path
from . import views

app_name = 'geofi'

urlpatterns = [
    path('', views.landing_page_view, name='landing'),
    path('novo-registro/', views.novo_registro_view, name='novo_registro'),
    path('remanejar-saldos/', views.remaneja_saldos_view, name='remaneja_saldos'),
]