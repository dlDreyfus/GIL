from django.contrib import admin
from .models import RegistroFinanceiro

@admin.register(RegistroFinanceiro)
class RegistroFinanceiroAdmin(admin.ModelAdmin):
    list_display = ('data', 'iniciativa', 'unidade_coordenacao', 'tipo_despesa', 'po')
    search_fields = ('iniciativa', 'unidade_coordenacao', 'po')
    list_filter = ('data', 'unidade_coordenacao', 'tipo_despesa')