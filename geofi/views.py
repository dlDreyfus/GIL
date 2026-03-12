from django.shortcuts import render
from .models import RegistroFinanceiro
from django.core.paginator import Paginator

def landing_page(request):
    # Ordena os registros pela data mais recente
    registros_list = RegistroFinanceiro.objects.all().order_by('-data')
    
    page_param = request.GET.get('page')
    per_page_param = request.GET.get('per_page', '25')
    is_showing_all = False

    if per_page_param == 'todos':
        total = registros_list.count()
        paginator = Paginator(registros_list, total if total > 0 else 1)
        is_showing_all = True
    else:
        try:
            per_page = int(per_page_param)
        except ValueError:
            per_page = 25
        paginator = Paginator(registros_list, per_page)

    page_obj = paginator.get_page(page_param)
    
    return render(request, 'geofi/landing.html', {'page_obj': page_obj, 'is_showing_all': is_showing_all, 'per_page': per_page_param})