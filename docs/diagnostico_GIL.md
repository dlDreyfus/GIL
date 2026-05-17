# 🔍 Diagnóstico Técnico — Projeto GIL

> **Engenheiro Django Sênior** | Análise completa do repositório clonado  
> Gerado em: 17/05/2026

---

## 1. Mapeamento Completo

### Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| **Backend** | Django | 5.1.6 |
| **Linguagem** | Python | 3.14 (venv) |
| **Banco Principal** | SQLite | `db.baseRO` |
| **Banco de Filtros** | SQLite | `db.filtrosRO` |
| **Processamento** | Pandas | 2.2.3 |
| **Excel** | openpyxl | 3.1.5 |
| **Moeda** | py-moneyed | 3.0 |
| **PDF** | weasyprint | 62.3 |
| **Deploy** | PythonAnywhere | — |
| **CSS** | Vanilla CSS (padrão Gov.br) | — |

### Arquitetura

```
GIL-1/
├── GIL/                    # Configuração do projeto (settings, urls, wsgi, asgi)
├── core/                   # App vazio (scaffold, sem lógica)
├── geofi/                  # App principal — CRUD de Registros Financeiros
│   ├── models.py           # Model: RegistroFinanceiro (17 campos)
│   ├── views.py            # 4 views: landing, novo, editar, apagar
│   ├── forms.py            # ModelForm com dropdowns dinâmicos via db.filtrosRO
│   ├── urls.py             # 4 rotas com namespace 'geofi'
│   ├── admin.py            # Admin registrado com list_display/filter
│   ├── migrations/         # 3 migrations (inicial + 2 alterações)
│   └── templates/geofi/    # 5 templates HTML
├── templates/base.html     # Template base (padrão visual Gov.br)
├── static/css/govbr.css    # CSS customizado Gov.br
├── db.baseRO               # Banco SQLite principal (commited no Git!)
├── db.filtrosRO            # Banco SQLite de filtros (commited no Git!)
├── db.sqlite3              # Banco SQLite padrão Django (commited no Git!)
├── load_data.py            # Script de carga (~79KB — muito grande)
├── venv/                   # Venv commited no Git!
└── geofi/requirements.txt  # requirements DENTRO do app (não na raiz)
```

### Fluxo de Dados

```
[Usuário] → POST (CSV upload) → landing_page_view
                                    ↓
                          RegistroFinanceiro.objects.all().delete()
                          RegistroFinanceiro.objects.bulk_create()
                                    ↓
                             db.baseRO (SQLite)

[Usuário] → GET /geofi/ → landing_page_view
                              ↓
                    RegistroFinanceiro.objects.annotate(Cast).order_by()
                              ↓
                    Paginator (25/50/100/todos)
                              ↓
                         landing.html (tabela)

[Formulários] → forms.py → get_opcoes() → sqlite3 direto em db.filtrosRO
```

### Apps e Responsabilidades

| App | Status | Responsabilidade |
|---|---|---|
| `core` | 🟡 Vazio | Scaffolded, sem modelos ou views |
| `geofi` | 🟢 Funcional | CRUD financeiro + importação CSV + exportação CSV |
| `django.contrib.humanize` | 🟢 Usado | `intcomma` no template para formatação de valores |

---

## 2. Diagnóstico: Riscos, Dívidas Técnicas e Pontos Fortes

### 🔴 Riscos Críticos

#### R1 — Secret Key exposta no `settings.py`
```python
# GIL/settings.py, linha 23
SECRET_KEY = 'django-insecure-&8!1uzed-!%*6d0f1o#nmml2@4hh4kdi0502k*swz1w6n8=rbi'
```
**Por quê é crítico:** A `SECRET_KEY` assina cookies de sessão, tokens CSRF e dados sensíveis. Com ela exposta no Git, qualquer pessoa que acesse o histórico pode forjar sessões, falsificar tokens CSRF e comprometer a integridade completa da aplicação. O prefixo `django-insecure-` confirma que é a chave gerada por padrão — nunca alterada.

#### R2 — `DEBUG = True` hardcoded (sem separação dev/prod)
```python
DEBUG = True  # settings.py linha 26
```
**Por quê é crítico:** Em produção no PythonAnywhere, `DEBUG=True` exibe tracebacks completos com variáveis locais, caminhos do servidor e configs para qualquer erro. Isso é um vetor de information disclosure grave.

#### R3 — Bancos de dados SQLite commitados no Git
```
db.baseRO   (295KB) — banco de dados principal com dados financeiros reais
db.filtrosRO (98KB) — banco de filtros
db.sqlite3  (213KB) — banco padrão Django
```
**Por quê é crítico:** Dados financeiros governamentais estão expostos no histórico do repositório. Uma vez no Git, mesmo deletando os arquivos, os dados continuam acessíveis via `git log`. Isso pode violar a LGPD e políticas de segurança do governo.

#### R4 — `venv/` commitado no Git
O diretório `venv/` está no repositório. Isso causa:
- Repositório inflado desnecessariamente
- Quebra de ambiente ao clonar em diferentes OS/arquiteturas
- O erro que você já encontrou: `ModuleNotFoundError: No module named 'django'` — a venv foi criada em outro caminho (`/home/dldreyfus/Downloads/GIL/venv`) e não funciona no novo caminho `GIL-1`

#### R5 — Views sem autenticação
```python
# Qualquer URL abaixo é acessível sem login:
/geofi/                         # visualiza toda a base financeira
/geofi/novo-registro/           # cria registros
/geofi/editar-registro/<id>/    # edita registros
/geofi/apagar-registro/<id>/    # apaga registros
```
**Por quê é crítico:** Não há `@login_required` em nenhuma view. Qualquer pessoa com o URL pode ler, inserir, editar e apagar dados financeiros governamentais.

---

### 🟠 Dívidas Técnicas (Alta Prioridade)

#### D1 — Upload CSV apaga toda a base sem confirmação
```python
# views.py, linha 104
RegistroFinanceiro.objects.all().delete()
RegistroFinanceiro.objects.bulk_create(objects_to_create)
```
**Por quê é problemático:** Uma operação destrutiva e irreversível acontece silenciosamente. Um CSV malformado ou enviado por engano destrói toda a base. Não há `transaction.atomic()`, sem backup, sem staging. O import deveria ser atômico.

#### D2 — Conexão raw SQLite em `forms.py` (bypass do ORM)
```python
# forms.py, linha 27
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT valor FROM Filtros WHERE campo = ? ORDER BY valor", (campo_db,))
```
**Por quê é problemático:** Quebra o padrão Django. Usa dois engines de banco de dado em paralelo (ORM + sqlite3 raw). Não há gerenciamento de transações, pooling de conexões, ou integração com o sistema de migrations. O banco `db.filtrosRO` deveria estar no `DATABASES` como `'filtros'` e ser acessado pelo ORM com `using='filtros'`.

#### D3 — `requirements.txt` dentro do app `geofi/` (não na raiz)
```
geofi/requirements.txt  ← errado
```
Convenção Django/Python é ter o `requirements.txt` na raiz do projeto. Qualquer CI/CD ou desenvolvedor novo não vai encontrá-lo no lugar esperado.

#### D4 — `linha_id` é `CharField` mas usado como inteiro
```python
# models.py
linha_id = models.CharField(max_length=10, ...)

# views.py — Cast necessário a cada query
.annotate(num_id=Cast('linha_id', output_field=IntegerField())).order_by('-num_id')
```
O campo deveria ser `IntegerField`. O Cast em toda query é um overhead desnecessário e indica que o tipo de dado está errado no modelo.

#### D5 — `load_data.py` de 79KB na raiz sem documentação
Um script de 79KB na raiz sem explicação de uso, sem CLI arguments, potencialmente com credenciais ou paths absolutos hardcoded.

#### D6 — `intcomma` formata valores no padrão americano (vírgula como milhares)
```html
R$ {{ r.ro_1|intcomma }}  → R$ 1,234,567.89  (errado para pt-br)
```
O `intcomma` do Django usa o padrão americano. Para valores em BRL, o correto seria `|floatformat:2|intcomma` com locale brasileiro ou um template filter customizado.

#### D7 — Quando `per_page = 'todos'`, `page_obj` é um queryset, não um Page object
```python
# views.py linhas 157-159
else:
    page_obj = registros_list  # QuerySet, não Page
```
O template chama `page_obj.has_previous`, `page_obj.number`, etc. — atributos que não existem em QuerySet. Isso quebra a paginação no modo "Todos".

#### D8 — `TIME_ZONE = 'UTC'` com app em português brasileiro
```python
TIME_ZONE = 'UTC'  # settings.py linha 113
```
O projeto está em pt-br mas salva timestamps em UTC sem conversão explícita. Para campos `DateField` não há problema, mas futuras funcionalidades com `DateTimeField` terão horários incorretos. Deveria ser `'America/Sao_Paulo'`.

---

### 🟡 Dívidas Técnicas (Média Prioridade)

#### D9 — `Exception` silenciada em `get_opcoes()`
```python
except Exception as e:
    pass  # forms.py linha 34
```
Engole qualquer erro de banco silenciosamente. Em dev, impossível saber se os dropdowns estão vazio por design ou por bug.

#### D10 — `fields = '__all__'` no ModelForm
```python
class Meta:
    fields = '__all__'  # forms.py linha 40
```
Expõe todos os campos, incluindo `linha_id` que é gerenciado pela view. Boa prática é listar os campos explicitamente.

#### D11 — Inline CSS massivo nos templates
Dezenas de `style=""` inline em `landing.html` e outros templates. Isso dificulta manutenção, duplica estilos e impede reutilização via CSS classes.

#### D12 — App `core` vazio instalado
```python
INSTALLED_APPS = [..., 'core', ...]
```
O app `core` tem apenas o scaffold padrão sem nenhuma lógica. Ou deve ser populado ou removido para não gerar confusão.

---

### 🟢 Pontos Fortes

| # | Ponto Forte | Detalhe |
|---|---|---|
| ✅ 1 | **CSRF ativo** | `{% csrf_token %}` presente nos formulários POST |
| ✅ 2 | **Paginação implementada** | Paginator com opções configuráveis (25/50/100/todos) |
| ✅ 3 | **Encoding robusto no CSV** | UTF-8 com BOM + fallback cp1252 — lida bem com Excel brasileiro |
| ✅ 4 | **Autodetecção de delimitador** | `;` vs `,` no CSV detectado automaticamente |
| ✅ 5 | **Validação de extensão no upload** | Verifica `.csv` antes de processar |
| ✅ 6 | **Admin configurado** | `list_display`, `search_fields`, `list_filter` registrados |
| ✅ 7 | **Namespace de URLs** | `app_name = 'geofi'` evita colisões de nomes |
| ✅ 8 | **Padrão visual Gov.br** | CSS customizado fiel ao design system governamental |
| ✅ 9 | **Migrations versionadas** | 3 migrations rastreando a evolução do schema |
| ✅ 10 | **BOM no CSV exportado** | `\ufeff` garante abertura correta no Excel BR |

---

## 3. Plano de Ações Priorizado

### 🔴 FASE 1 — Setup Local (Fazer AGORA, antes de qualquer outra coisa)

#### Ação 1.1 — Criar e ativar venv corretamente

```bash
# Na pasta do projeto
cd /home/dldreyfus/Downloads/GIL-1

# Criar nova venv com python3 do sistema
python3 -m venv venv

# Ativar
source venv/bin/activate

# Instalar dependências
pip install -r geofi/requirements.txt
```

**Por quê:** A venv commitada foi criada no path `GIL/venv` e referencia `/usr/bin/python3.14`. Ao clonar para `GIL-1`, todos os paths absolutos internos à venv estão quebrados — daí o `ModuleNotFoundError`.

#### Ação 1.2 — Criar `.gitignore` imediatamente

```gitignore
# .gitignore — criar na raiz do projeto

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd

# Ambientes virtuais
venv/
.venv/
env/

# Bancos de dados SQLite — NUNCA commitar dados!
*.sqlite3
db.baseRO
db.filtrosRO

# Django
staticfiles/
media/
*.log

# Segredos
.env
*.env

# IDEs
.idea/
.vscode/
*.swp
```

**Por quê:** Sem `.gitignore`, o Git rastreia venv, bancos de dados e futuramente arquivos `.env` com segredos. Dados financeiros já estão no histórico — pelo menos evitar que mais dados entrem.

#### Ação 1.3 — Mover `requirements.txt` para a raiz

```bash
cp geofi/requirements.txt ./requirements.txt
```

**Por quê:** Convenção universal Python/Django. Ferramentas como pip, Docker, Heroku, PythonAnywhere e qualquer CI esperam `requirements.txt` na raiz.

#### Ação 1.4 — Aplicar migrations no banco local

```bash
source venv/bin/activate
python3 manage.py migrate
python3 manage.py runserver
```

---

### 🔴 FASE 2 — Segurança (Crítico — não subir para produção sem isso)

#### Ação 2.1 — Criar arquivo `.env` e mover segredos

```bash
pip install python-decouple
```

Criar `.env` na raiz:
```env
# .env — NUNCA commitar este arquivo!
SECRET_KEY=gere-uma-nova-chave-aqui
DEBUG=False
ALLOWED_HOSTS=dldreyfus.pythonanywhere.com,localhost,127.0.0.1
```

Gerar uma nova SECRET_KEY:
```bash
python3 -c "from django.core.signing import get_cookie_signer; from django.utils.crypto import get_random_string; print(get_random_string(50))"
```

Atualizar `settings.py`:
```python
# settings.py — topo do arquivo
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')
```

**Por quê:** A chave atual está exposta no Git e deve ser considerada comprometida. Qualquer segredo em `settings.py` fica no histórico de commits para sempre. `python-decouple` é a solução mais simples e idiomática para Django.

#### Ação 2.2 — Proteger todas as views com `@login_required`

```python
# geofi/views.py
from django.contrib.auth.decorators import login_required

@login_required
def landing_page_view(request):
    ...

@login_required
def novo_registro_view(request):
    ...

@login_required
def edita_registro_view(request, id):
    ...

@login_required
def apaga_registro_view(request, id):
    ...
```

Adicionar ao `settings.py`:
```python
LOGIN_URL = '/admin/login/'  # Redireciona para o login do admin Django
```

**Por quê:** Dados financeiros governamentais não devem ser acessíveis publicamente. O decorator redireciona usuários não autenticados para login sem precisar construir um sistema de autenticação separado.

#### Ação 2.3 — Corrigir upload CSV com `transaction.atomic()`

```python
# views.py — bloco de importação
from django.db import transaction

if objects_to_create:
    with transaction.atomic():  # ← operação atômica
        RegistroFinanceiro.objects.all().delete()
        RegistroFinanceiro.objects.bulk_create(objects_to_create)
```

**Por quê:** Sem `atomic()`, se `bulk_create` falhar na metade, a base ficará vazia (delete já executou). Com `atomic()`, se qualquer operação falhar, o banco volta ao estado anterior automaticamente.

---

### 🟠 FASE 3 — Validação e Correções de Bug

#### Ação 3.1 — Corrigir o modo "Todos" no paginador

```python
# views.py — refatorar a lógica de paginação
if per_page != 'todos':
    paginator = Paginator(registros_list, int(per_page))
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    is_paginated = True
else:
    page_obj = registros_list
    is_paginated = False

return render(request, 'geofi/landing.html', {
    'page_obj': page_obj,
    'per_page': per_page,
    'is_paginated': is_paginated,  # controle no template
})
```

No template, envolver os controles de paginação com `{% if is_paginated %}`.

**Por quê:** Quando `per_page='todos'`, `page_obj` é um QuerySet. Chamar `page_obj.has_previous` levanta `AttributeError`. Isso é um bug real que pode quebrar a página.

#### Ação 3.2 — Corrigir `linha_id` para `IntegerField`

```python
# models.py
linha_id = models.IntegerField(verbose_name="ID", null=True, blank=True)
```

```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

**Por quê:** Elimina o `Cast` em toda query de ordenação/agregação, simplifica a lógica de `max_val` e `proximo_id`, e reflete corretamente o tipo de dado armazenado.

#### Ação 3.3 — Corrigir TIME_ZONE

```python
# settings.py
TIME_ZONE = 'America/Sao_Paulo'
```

#### Ação 3.4 — Logar erros silenciados em `get_opcoes()`

```python
import logging
logger = logging.getLogger(__name__)

def get_opcoes(campo_db):
    ...
    try:
        ...
    except Exception as e:
        logger.error(f"Erro ao buscar opções para campo '{campo_db}': {e}")
    return opcoes
```

---

### 🟡 FASE 4 — Melhorias e Boas Práticas

#### Ação 4.1 — Migrar `db.filtrosRO` para o ORM

Adicionar ao `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.baseRO',
    },
    'filtros': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.filtrosRO',
    }
}
```

Criar model em `geofi/models.py`:
```python
class FiltroOpcao(models.Model):
    campo = models.CharField(max_length=100)
    valor = models.CharField(max_length=255)

    class Meta:
        db_table = 'Filtros'  # usa a tabela existente
```

Usar no `forms.py`:
```python
from .models import FiltroOpcao

def get_opcoes(campo_db):
    opcoes = [('', 'Selecione')]
    opcoes += list(
        FiltroOpcao.objects.using('filtros')
        .filter(campo=campo_db)
        .order_by('valor')
        .values_list('valor', 'valor')
    )
    return opcoes
```

**Por quê:** Elimina a conexão raw com `sqlite3`, usa o pooling do ORM, fica sujeito a migrations e torna o código testável.

#### Ação 4.2 — Definir `fields` explícitos no ModelForm

```python
class RegistroFinanceiroForm(forms.ModelForm):
    class Meta:
        model = RegistroFinanceiro
        fields = [
            'data', 'mes', 'periodo', 'arquivo', 'rf_sub',
            'unidade_coordenacao', 'grupos', 'despesa_gerencial',
            'iniciativa', 'gnd', 'tipo_despesa', 'ro_1', 'lme_1',
            'po', 'acao', 'po_gnd'
        ]
        # linha_id é gerenciado pela view, não pelo form
```

#### Ação 4.3 — Corrigir formatação de moeda (pt-br)

```python
# geofi/templatetags/currency_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def brl(value):
    """Formata Decimal para padrão brasileiro: R$ 1.234.567,89"""
    if value is None:
        return ''
    try:
        valor = Decimal(value)
        inteiro = int(abs(valor))
        centavos = abs(valor) - inteiro
        inteiro_fmt = f"{inteiro:,}".replace(",", ".")
        centavos_fmt = f"{centavos:.2f}"[1:].replace(".", ",")
        sinal = "-" if valor < 0 else ""
        return f"R$ {sinal}{inteiro_fmt}{centavos_fmt}"
    except Exception:
        return str(value)
```

#### Ação 4.4 — Adicionar configuração de logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'geofi': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

#### Ação 4.5 — Criar testes mínimos

```python
# geofi/tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import RegistroFinanceiro

class LandingPageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('teste', password='senha123')

    def test_redirect_sem_login(self):
        response = self.client.get('/geofi/')
        self.assertEqual(response.status_code, 302)  # redireciona para login

    def test_acesso_com_login(self):
        self.client.login(username='teste', password='senha123')
        response = self.client.get('/geofi/')
        self.assertEqual(response.status_code, 200)
```

---

## Resumo dos Passos Para Rodar Agora

```bash
# 1. Na pasta do projeto, criar venv nova
cd /home/dldreyfus/Downloads/GIL-1
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r geofi/requirements.txt

# 3. Criar .env com SECRET_KEY
echo "SECRET_KEY=$(python3 -c "from django.utils.crypto import get_random_string; print(get_random_string(50))")" > .env
echo "DEBUG=True" >> .env
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env

# 4. Instalar python-decouple e atualizar settings
pip install python-decouple

# 5. Rodar migrations
python3 manage.py migrate

# 6. Criar superusuário para acessar o admin
python3 manage.py createsuperuser

# 7. Subir o servidor
python3 manage.py runserver
```

---

## 📋 Resumo Executivo — 5 Bullets

1. **🔴 Segurança comprometida em múltiplos pontos:** `SECRET_KEY` exposta no Git (deve ser considerada comprometida e rotacionada imediatamente), nenhuma view protegida por autenticação e dados financeiros SQLite commitados no repositório — três violações críticas que precisam ser corrigidas antes de qualquer deploy.

2. **🔧 A falha do `runserver` é estrutural:** A `venv/` foi commitada com paths absolutos do ambiente original (`GIL/venv`), tornando-a incompatível com o clone atual (`GIL-1`). A solução é criar uma nova venv localmente e instalar `geofi/requirements.txt` — **não há Django instalado no sistema, apenas dentro de uma venv quebrada**.

3. **🐛 Bug real em produção:** O modo "Exibir Todos" na paginação (`per_page=todos`) passa um QuerySet onde o template espera um Page object, causando `AttributeError` ao renderizar `page_obj.has_previous`. Este bug afeta usuários que selecionam a opção "Todas" na landing page.

4. **📐 Arquitetura funcional mas com débito técnico acumulado:** O core do sistema (importação CSV atômica, paginação, CRUD, exportação CSV, detecção de encoding) está bem implementado. O principal débito é o bypass do ORM via `sqlite3` raw para os filtros e o tipo incorreto de `linha_id` (CharField tratado como inteiro em toda query).

5. **🚀 Caminho de melhoria claro e incremental:** A prioridade imediata é: `(1)` criar nova venv → `(2)` adicionar `.gitignore` → `(3)` mover segredos para `.env` → `(4)` proteger views com `@login_required` → `(5)` corrigir `transaction.atomic()` no upload. Com essas 5 ações, o projeto passa de "arriscado" para "operacionalmente seguro".
