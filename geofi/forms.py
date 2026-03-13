from django import forms
from .models import RegistroFinanceiro
from django.core.exceptions import ValidationError

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


class RegistroModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.linha_id} - {obj.iniciativa} - {obj.unidade_coordenacao} - {obj.data.strftime('%d/%m/%Y') if obj.data else ''}"

class RemanejaSaldosForm(forms.Form):
    registro_origem = RegistroModelChoiceField(
        queryset=RegistroFinanceiro.objects.all().order_by('-id'),
        label="Registro de Origem (de onde o saldo será subtraído)",
        widget=forms.Select(attrs={'class': 'select2-widget'})
    )
    registro_destino = RegistroModelChoiceField(
        queryset=RegistroFinanceiro.objects.all().order_by('-id'),
        label="Registro de Destino (para onde o saldo será adicionado)",
        widget=forms.Select(attrs={'class': 'select2-widget'})
    )
    valor_ro1 = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        label="Valor a Remanejar (RO-1)",
        required=False,
        help_text="Valor a ser transferido do saldo RO-1."
    )
    valor_lme1 = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        label="Valor a Remanejar (LME-1)",
        required=False,
        help_text="Valor a ser transferido do saldo LME-1."
    )

    def clean(self):
        cleaned_data = super().clean()
        origem = cleaned_data.get("registro_origem")
        destino = cleaned_data.get("registro_destino")

        if origem and destino and origem == destino:
            raise ValidationError("O registro de origem não pode ser o mesmo que o de destino.")
        
        if not cleaned_data.get('valor_ro1') and not cleaned_data.get('valor_lme1'):
            raise ValidationError("Informe pelo menos um valor para remanejar (RO-1 ou LME-1).")
            
        return cleaned_data