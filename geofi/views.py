from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from .models import RegistroFinanceiro
from .forms import RegistroFinanceiroForm, RemanejaSaldosForm
from django.db import transaction
from decimal import Decimal

# View que renderiza a sua landing page com a tabela
def landing_page_view(request):
    registros_list = RegistroFinanceiro.objects.all().order_by('-data', '-id')
    
    per_page = request.GET.get('per_page', '25')

    if per_page != 'todos':
        paginator = Paginator(registros_list, int(per_page))
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        # Se "todos", não paginar
        page_obj = registros_list

    return render(request, 'geofi/landing.html', {
        'page_obj': page_obj,
        'per_page': per_page
    })

# View para a página de "Novo Registro"
def novo_registro_view(request):
    if request.method == 'POST':
        form = RegistroFinanceiroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Novo registro adicionado com sucesso!')
            return redirect('geofi:landing')
    else:
        form = RegistroFinanceiroForm()
    return render(request, 'geofi/novoRegistroBaseRo.html', {'form': form})

@transaction.atomic
def remaneja_saldos_view(request):
    if request.method == 'POST':
        form = RemanejaSaldosForm(request.POST)
        if form.is_valid():
            origem = form.cleaned_data['registro_origem']
            destino = form.cleaned_data['registro_destino']
            valor = form.cleaned_data['valor']

            # Coalesce None to 0 before arithmetic
            origem.ro_1 = (origem.ro_1 or Decimal('0.0')) - valor
            origem.lme_1 = (origem.lme_1 or Decimal('0.0')) - valor
            
            destino.ro_1 = (destino.ro_1 or Decimal('0.0')) + valor
            destino.lme_1 = (destino.lme_1 or Decimal('0.0')) + valor

            origem.save()
            destino.save()

            messages.success(request, f"Valor de R$ {valor} remanejado com sucesso da iniciativa '{origem.iniciativa}' para '{destino.iniciativa}'.")
            return redirect('geofi:landing')
    else:
        form = RemanejaSaldosForm()
    
    return render(request, 'geofi/remanejaSaldos.html', {'form': form})