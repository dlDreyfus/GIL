from django import forms
from .models import RegistroFinanceiro
from django.core.exceptions import ValidationError
import sqlite3
import os
from django.conf import settings

FIELD_MAPPING = {
    'mes': 'MES',
    'rf_sub': 'RF_SUB',
    'unidade_coordenacao': 'UNID_COORD',
    'grupos': 'GRUPO',
    'despesa_gerencial': 'DESP_GERENCIAL',
    'iniciativa': 'INICIATIVA',
    'gnd': 'GND',
    'tipo_despesa': 'TIPO_DESPESA',
    'po': 'PO',
    'acao': 'ACAO',
    'po_gnd': 'PO_GND',
}

def get_opcoes(campo_db):
    db_path = os.path.join(settings.BASE_DIR, 'db.filtrosRO')
    opcoes = [('', 'Selecione')]
    if not os.path.exists(db_path):
        return opcoes
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Filtros WHERE campo = ? ORDER BY valor", (campo_db,))
        for row in cursor.fetchall():
            opcoes.append((row[0], row[0]))
        conn.close()
    except Exception as e:
        pass
    return opcoes

class RegistroFinanceiroForm(forms.ModelForm):
    class Meta:
        model = RegistroFinanceiro
        fields = '__all__'
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = field.label or field_name
            if field_name in FIELD_MAPPING:
                opcoes = get_opcoes(FIELD_MAPPING[field_name])
                self.fields[field_name].widget = forms.Select(choices=opcoes)
                self.fields[field_name].widget.attrs['class'] = 'select2-field form-control'
                self.fields[field_name].widget.attrs['style'] = 'padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; width: 100%; background-color: #fff;'