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


class RemanejaSaldosForm(forms.Form):
    registro_origem = forms.ModelChoiceField(
        queryset=RegistroFinanceiro.objects.all().order_by('iniciativa', '-data'),
        label="Registro de Origem (de onde o saldo será subtraído)",
        widget=forms.Select(attrs={'class': 'select2-widget'})
    )
    registro_destino = forms.ModelChoiceField(
        queryset=RegistroFinanceiro.objects.all().order_by('iniciativa', '-data'),
        label="Registro de Destino (para onde o saldo será adicionado)",
        widget=forms.Select(attrs={'class': 'select2-widget'})
    )
    valor = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        label="Valor a Remanejar",
        help_text="Use valores positivos. O valor será subtraído da origem e somado ao destino."
    )

    def clean(self):
        cleaned_data = super().clean()
        origem = cleaned_data.get("registro_origem")
        destino = cleaned_data.get("registro_destino")

        if origem and destino and origem == destino:
            raise ValidationError("O registro de origem não pode ser o mesmo que o de destino.")
        return cleaned_data