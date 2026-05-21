from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib import messages
from .models import RegistroFinanceiro
from django.db import transaction
from .forms import RegistroFinanceiroForm, FIELD_MAPPING, get_opcoes
from decimal import Decimal
import json
import csv
import os
from django.conf import settings
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

def atualiza_campo_view(request, id):
    """Endpoint AJAX para atualizar um campo individual de um RegistroFinanceiro."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    campo = data.get('campo')
    valor = data.get('valor')

    # Campos que podem ser editados inline (exclui id, pk, linha_id)
    campos_permitidos = [
        'data', 'mes', 'periodo', 'arquivo', 'rf_sub', 'unidade_coordenacao',
        'grupos', 'despesa_gerencial', 'iniciativa', 'gnd', 'tipo_despesa',
        'ro_1', 'lme_1', 'po', 'acao', 'po_gnd',
    ]

    if campo not in campos_permitidos:
        return JsonResponse({'ok': False, 'erro': f'Campo "{campo}" não é editável.'}, status=400)

    registro = get_object_or_404(RegistroFinanceiro, id=id)

    # Converte o valor conforme o tipo do campo no model
    field = RegistroFinanceiro._meta.get_field(campo)

    try:
        if field.get_internal_type() == 'DecimalField':
            if valor is None or str(valor).strip() == '':
                valor = None
            else:
                # Aceita tanto formato BR (1.234,56) quanto padrão (1234.56)
                cleaned = str(valor).replace('R$', '').replace(' ', '').strip()
                if ',' in cleaned:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                valor = Decimal(cleaned)
        elif field.get_internal_type() == 'DateField':
            if valor is None or str(valor).strip() == '':
                valor = None
            else:
                valor_str = str(valor).strip()
                # Aceita DD/MM/YYYY ou YYYY-MM-DD
                if '/' in valor_str:
                    valor = datetime.strptime(valor_str, '%d/%m/%Y').date()
                else:
                    valor = datetime.strptime(valor_str[:10], '%Y-%m-%d').date()
    except (ValueError, Exception) as e:
        return JsonResponse({'ok': False, 'erro': f'Valor inválido para o campo "{campo}": {str(e)}'}, status=400)

    setattr(registro, campo, valor)
    registro.save(update_fields=[campo])

    # Retorna o valor formatado para exibir na célula
    valor_display = valor
    if field.get_internal_type() == 'DecimalField' and valor is not None:
        from django.contrib.humanize.templatetags.humanize import intcomma
        valor_display = f'R$ {intcomma(valor)}'
    elif field.get_internal_type() == 'DateField' and valor is not None:
        valor_display = valor.strftime('%d/%m/%Y')
    else:
        valor_display = str(valor) if valor is not None else ''

    return JsonResponse({'ok': True, 'valor_display': valor_display})

def opcoes_campo_view(request, campo):
    """
    Retorna as opções de dropdown para um campo específico (consulta db.filtrosRO).
    """
    if campo not in FIELD_MAPPING:
        return JsonResponse({'opcoes': []}, status=400)
    opcoes_raw = get_opcoes(FIELD_MAPPING[campo])
    # Remove a opção vazia 'Selecione' — no inline edit não faz sentido
    opcoes = [val for val, _ in opcoes_raw if val != '']
    return JsonResponse({'opcoes': opcoes})


def filtros_cascata_view(request):
    """
    Retorna opções para todos os campos de seleção consultando db.filtrosRO.
    - rf_sub e unidade_coordenacao: DISTINCT sem filtro (não participam da cascata).
    - grupos em diante: filtros em cascata, cada campo filtrado pelos anteriores.
    """
    import sqlite3

    standalone = [
        ('rf_sub', 'RF_SUB'),
        ('unidade_coordenacao', 'UNID_COORD'),
    ]

    cascade_chain = [
        ('grupos',              'GRUPO'),
        ('despesa_gerencial',   'DESP_GERENCIAL'),
        ('iniciativa',          'INICIATIVA'),
        ('gnd',                 'GND'),
        ('tipo_despesa',        'TIPO_DESPESA'),
        ('po',                  'PO'),
        ('acao',                'ACAO'),
        ('po_gnd',              'PO_GND'),
    ]

    db_path = os.path.join(settings.BASE_DIR, 'db.filtrosRO')
    result = {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for form_name, db_col in standalone:
            cursor.execute(
                f'SELECT DISTINCT "{db_col}" FROM Registros '
                f'WHERE "{db_col}" IS NOT NULL AND "{db_col}" != "" '
                f'ORDER BY "{db_col}"'
            )
            result[form_name] = [row[0] for row in cursor.fetchall() if row[0]]

        for i, (form_name, db_col) in enumerate(cascade_chain):
            conditions = []
            params = []
            for prev_form, prev_db in cascade_chain[:i]:
                val = request.GET.get(prev_form, '').strip()
                if val:
                    conditions.append(f'"{prev_db}" = ?')
                    params.append(val)

            query = f'SELECT DISTINCT "{db_col}" FROM Registros'
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            query += f' ORDER BY "{db_col}"'

            cursor.execute(query, params)
            result[form_name] = [row[0] for row in cursor.fetchall() if row[0]]

        conn.close()
    except Exception as e:
        result['erro'] = str(e)

    return JsonResponse(result)


def auto_fill_cascata_view(request):
    """
    A partir do campo indicado em `changed_field`, retorna para cada campo
    seguinte na cadeia: a lista de opções (opcoes) e o primeiro valor disponível
    (valor) como sugestão de auto-preenchimento.

    Cada valor auto-selecionado é usado como filtro para os campos subsequentes,
    garantindo que a cascata seja calculada corretamente de ponta a ponta.
    """
    import sqlite3

    cascade_chain = [
        ('grupos',              'GRUPO'),
        ('despesa_gerencial',   'DESP_GERENCIAL'),
        ('iniciativa',          'INICIATIVA'),
        ('gnd',                 'GND'),
        ('tipo_despesa',        'TIPO_DESPESA'),
        ('po',                  'PO'),
        ('acao',                'ACAO'),
        ('po_gnd',              'PO_GND'),
    ]

    changed_field = request.GET.get('changed_field', '').strip()
    start_idx = next((i for i, (f, _) in enumerate(cascade_chain) if f == changed_field), -1)
    if start_idx == -1:
        return JsonResponse({'erro': 'Campo inválido'}, status=400)

    # Coleta os valores atuais dos campos até e incluindo o campo alterado
    current_vals = {}
    for form_name, _ in cascade_chain[:start_idx + 1]:
        val = request.GET.get(form_name, '').strip()
        if val:
            current_vals[form_name] = val

    db_path = os.path.join(settings.BASE_DIR, 'db.filtrosRO')
    result = {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for i, (form_name, db_col) in enumerate(cascade_chain):
            if i <= start_idx:
                continue

            conditions = []
            params = []
            for j, (prev_form, prev_db) in enumerate(cascade_chain[:i]):
                val = current_vals.get(prev_form, '')
                if val:
                    conditions.append(f'"{prev_db}" = ?')
                    params.append(val)

            query = f'SELECT DISTINCT "{db_col}" FROM Registros'
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            query += f' ORDER BY "{db_col}"'

            cursor.execute(query, params)
            opcoes = [row[0] for row in cursor.fetchall() if row[0]]

            primeiro = opcoes[0] if opcoes else ''
            # Usa o primeiro valor como filtro para os campos seguintes
            if primeiro:
                current_vals[form_name] = primeiro

            result[form_name] = {'opcoes': opcoes, 'valor': primeiro}

        conn.close()
    except Exception as e:
        result['erro'] = str(e)

    return JsonResponse(result)