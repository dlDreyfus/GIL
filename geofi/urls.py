from django.urls import path
from . import views

app_name = 'geofi'

urlpatterns = [
    path('', views.landing_page_view, name='landing'),
    path('novo-registro/', views.novo_registro_view, name='novo_registro'),
    path('editar-registro/<int:id>/', views.edita_registro_view, name='edita_registro'),
    path('apagar-registro/<int:id>/', views.apaga_registro_view, name='apaga_registro'),
    path('api/atualizar-campo/<int:id>/', views.atualiza_campo_view, name='atualiza_campo'),
    path('api/opcoes-campo/<str:campo>/', views.opcoes_campo_view, name='opcoes_campo'),
]