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
from datetime import datetime

def parse_currency(value_str):
    """Converte uma string de moeda no formato brasileiro para um objeto Decimal."""
    if not value_str:
        return None
    value_str = str(value_str).strip()
    if not value_str or value_str == '-' or value_str == '#N/D':
        return None
    try:
        # Remove o separador de milhares (.) e substitui a vírgula decimal (,) por ponto (.)
        cleaned_str = value_str.replace('.', '').replace(',', '.')
        return Decimal(cleaned_str)
    except Exception:
        return None

# View que renderiza a sua landing page com a tabela
def landing_page_view(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'O arquivo não é um CSV válido.')
            return redirect('geofi:landing')
            
        try:
            # Processa o arquivo CSV recebido
            raw_data = csv_file.read()
            
            # Tenta decodificar como UTF-8, com fallback para ANSI (padrão do Excel no Brasil)
            try:
                file_string = raw_data.decode('utf-8-sig')
            except UnicodeDecodeError:
                file_string = raw_data.decode('cp1252')
                
            file_lines = file_string.splitlines()
            
            # Autodetecta o delimitador (; ou ,)
            delimiter = ';' if ';' in file_lines[0] else ','
            reader = csv.DictReader(file_lines, delimiter=delimiter)
            
            objects_to_create = []
            for row in reader:
                # Ignora linhas vazias de forma segura (previne erro se o valor for None ou Lista)
                is_empty = True
                for val in row.values():
                    if isinstance(val, str) and val.strip():
                        is_empty = False
                        break
                    elif isinstance(val, list) and any(isinstance(v, str) and v.strip() for v in val):
                        is_empty = False
                        break
                
                if is_empty:
                    continue
                
                date_str = str(row.get('Data') or '').strip()
                date_obj = None
                if date_str:
                    try:
                        # Suporta o formato YYYY-MM-DD e DD/MM/YYYY
                        if '-' in date_str:
                            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                        else:
                            date_obj = datetime.strptime(date_str[:10], '%d/%m/%Y').date()
                    except ValueError:
                        pass
                
                obj = RegistroFinanceiro(
                    linha_id=str(row.get('ID') or '')[:10],
                    data=date_obj,
                    mes=str(row.get('Mês') or '')[:20],
                    periodo=str(row.get('Período') or '')[:50],
                    arquivo=str(row.get('Arquivo') or '')[:255],
                    rf_sub=str(row.get('RF-SUB') or '')[:100],
                    unidade_coordenacao=str(row.get('Unidade/Coord.') or '')[:255],
                    grupos=str(row.get('Grupos') or '')[:255],
                    despesa_gerencial=str(row.get('Despesa Gerencial') or '')[:255],
                    iniciativa=str(row.get('Iniciativa') or '')[:255],
                    gnd=str(row.get('GND') or '')[:100],
                    tipo_despesa=str(row.get('Tipo Despesa') or '')[:255],
                    ro_1=parse_currency(row.get('RO-1')),
                    lme_1=parse_currency(row.get('LME-1')),
                    po=str(row.get('PO') or '')[:100],
                    acao=str(row.get('Ação') or '')[:255],
                    po_gnd=str(row.get('PO+GND') or '')[:100]
                )
                objects_to_create.append(obj)
                
            if objects_to_create:
                # Exclui todos os registros antigos e insere os novos em lote
                RegistroFinanceiro.objects.all().delete()
                RegistroFinanceiro.objects.bulk_create(objects_to_create)
                messages.success(request, f'Base atualizada com sucesso! {len(objects_to_create)} registros importados.')
            else:
                messages.warning(request, 'O arquivo CSV selecionado estava vazio ou sem registros válidos.')
                
        except Exception as e:
            messages.error(request, f'Erro ao processar o arquivo CSV: {str(e)}')
            print("Erro no upload do CSV:", e)  # Log no console para rastreamento
            
        return redirect('geofi:landing')

    registros_list = RegistroFinanceiro.objects.annotate(
        num_id=Cast('linha_id', output_field=IntegerField())
    ).order_by('-num_id')
    
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