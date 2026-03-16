from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib import messages
from .models import RegistroFinanceiro
from .forms import RegistroFinanceiroForm, RemanejaSaldosForm
from django.db import transaction
from decimal import Decimal
import json
import csv
from django.db.models import Max, IntegerField
from django.db.models.functions import Cast

# View que renderiza a sua landing page com a tabela
def landing_page_view(request):
    registros_list = RegistroFinanceiro.objects.all().order_by('-data', '-id')
    
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="base_ro.csv"'
        response.write('\ufeff') # Permite que o Excel abra o arquivo UTF-8 corretamente
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['ID', 'Data', 'Mês', 'Período', 'Arquivo', 'RF-SUB', 'Unidade/Coord.', 'Grupos', 'Despesa Gerencial', 'Iniciativa', 'GND', 'Tipo Despesa', 'RO-1', 'LME-1', 'PO', 'Ação', 'PO+GND'])
        
        for r in registros_list:
            writer.writerow([
                r.linha_id,
                r.data.strftime('%d/%m/%Y') if r.data else '',
                r.mes,
                r.periodo,
                r.arquivo,
                r.rf_sub,
                r.unidade_coordenacao,
                r.grupos,
                r.despesa_gerencial,
                r.iniciativa,
                r.gnd,
                r.tipo_despesa,
                str(r.ro_1).replace('.', ',') if r.ro_1 is not None else '',
                str(r.lme_1).replace('.', ',') if r.lme_1 is not None else '',
                r.po,
                r.acao,
                r.po_gnd
            ])
            
        return response

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
    # Lógica para calcular o próximo ID (linha_id) de forma incremental
    # Converte o campo 'linha_id' (string) para Inteiro para garantir que o Max considere a ordem numérica
    max_val = RegistroFinanceiro.objects.annotate(
        num_id=Cast('linha_id', output_field=IntegerField())
    ).aggregate(Max('num_id'))['num_id__max']
    
    # Se max_val for None (banco vazio), começa do 1, senão incrementa
    proximo_id = (max_val or 0) + 1

    if request.method == 'POST':
        form = RegistroFinanceiroForm(request.POST)
        if form.is_valid():
            # Força o salvamento do ID calculado (ignora o que vier do form, pois o campo está disabled)
            form.instance.linha_id = str(proximo_id)
            form.save()
            messages.success(request, f'Novo registro adicionado com sucesso! (ID: {proximo_id})')
            return redirect('geofi:landing')
    else:
        form = RegistroFinanceiroForm()
    return render(request, 'geofi/novoRegistroBaseRo.html', {'form': form, 'proximo_id': proximo_id})

def edita_registro_view(request, id):
    registro = get_object_or_404(RegistroFinanceiro, id=id)
    
    if request.method == 'POST':
        form = RegistroFinanceiroForm(request.POST, instance=registro)
        if form.is_valid():
            form.save()
            messages.success(request, f'Registro {registro.linha_id} atualizado com sucesso!')
            return redirect('geofi:landing')
    else:
        form = RegistroFinanceiroForm(instance=registro)
    
    return render(request, 'geofi/editaRegistroBaseRo.html', {'form': form, 'registro': registro})

def apaga_registro_view(request, id):
    registro = get_object_or_404(RegistroFinanceiro, id=id)
    
    if request.method == 'POST':
        registro.delete()
        messages.success(request, f'Registro {registro.linha_id or registro.id} excluído com sucesso!')
        return redirect('geofi:landing')
    
    form = RegistroFinanceiroForm(instance=registro)
    for field in form.fields.values():
        field.widget.attrs['disabled'] = True
    
    return render(request, 'geofi/apagaRegistroBaseRo.html', {'form': form, 'registro': registro})

@transaction.atomic
def remaneja_saldos_view(request):
    # Lógica AJAX: Se a requisição for AJAX e tiver um registro_id, retorna os detalhes em JSON
    if (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == 'true') and request.GET.get('registro_id'):
        registro_id = request.GET.get('registro_id')
        try:
            r = RegistroFinanceiro.objects.get(id=registro_id)
            data = {
                'id': r.id,
                # Formato ISO para preencher inputs type="date"
                'data': r.data.strftime('%Y-%m-%d') if r.data else '',
                # Formato visual
                'data_display': r.data.strftime('%d/%m/%Y') if r.data else '-',
                'mes': r.mes or '-',
                'periodo': r.periodo or '-',
                'arquivo': r.arquivo or '-',
                'rf_sub': r.rf_sub or '-',
                'unidade_coordenacao': r.unidade_coordenacao or '-',
                'grupos': r.grupos or '-',
                'despesa_gerencial': r.despesa_gerencial or '-',
                'iniciativa': r.iniciativa or '-',
                'gnd': r.gnd or '-',
                'tipo_despesa': r.tipo_despesa or '-',
                'ro_1': float(r.ro_1) if r.ro_1 is not None else 0.0,
                'lme_1': float(r.lme_1) if r.lme_1 is not None else 0.0,
                'po': r.po or '-',
                'acao': r.acao or '-',
                'po_gnd': r.po_gnd or '-'
            }
            return JsonResponse(data)
        except RegistroFinanceiro.DoesNotExist:
            return JsonResponse({'error': 'Registro não encontrado'}, status=404)

    if request.method == 'POST':
        form = RemanejaSaldosForm(request.POST)
        if form.is_valid():
            origem = form.cleaned_data['registro_origem']
            destino = form.cleaned_data['registro_destino']
            
            # Obtém valores, assumindo 0.0 se o campo estiver vazio
            val_ro1 = form.cleaned_data.get('valor_ro1') or Decimal('0.0')
            val_lme1 = form.cleaned_data.get('valor_lme1') or Decimal('0.0')

            # Coalesce None to 0 before arithmetic
            origem.ro_1 = (origem.ro_1 or Decimal('0.0')) - val_ro1
            origem.lme_1 = (origem.lme_1 or Decimal('0.0')) - val_lme1
            
            destino.ro_1 = (destino.ro_1 or Decimal('0.0')) + val_ro1
            destino.lme_1 = (destino.lme_1 or Decimal('0.0')) + val_lme1

            origem.save()
            destino.save()

            messages.success(request, f"Remanejamento realizado com sucesso! (RO-1: R$ {val_ro1} | LME-1: R$ {val_lme1})")
            return redirect('geofi:landing')
    else:
        form = RemanejaSaldosForm()
    
    return render(request, 'geofi/remanejaSaldos.html', {'form': form})