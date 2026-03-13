from django.db import models

class RegistroFinanceiro(models.Model):
    data = models.DateField(verbose_name="DATA")
    mes = models.CharField(max_length=20, verbose_name="Mês")
    periodo = models.CharField(max_length=50, verbose_name="Período")
    arquivo = models.CharField(max_length=255, verbose_name="ARQUIVO")
    rf_sub = models.CharField(max_length=100, verbose_name="RF-SUB")
    unidade_coordenacao = models.CharField(max_length=255, verbose_name="Unidade/Coordenação")
    grupos = models.CharField(max_length=255, verbose_name="Grupos")
    despesa_gerencial = models.CharField(max_length=255, verbose_name="Despesa Gerencial")
    iniciativa = models.CharField(max_length=255, verbose_name="Iniciativa")
    # SUGESTÃO DE NORMALIZAÇÃO: Campos com valores repetidos como 'gnd', 'unidade_coordenacao',
    # 'iniciativa', etc., são candidatos a se tornarem modelos separados com chaves estrangeiras (ForeignKey).
    # Exemplo: gnd = models.ForeignKey('GrupoNaturezaDespesa', on_delete=models.PROTECT)
    gnd = models.CharField(max_length=100, verbose_name="GND")
    tipo_despesa = models.CharField(max_length=255, verbose_name="Tipo de Despesa")
    ro_1 = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="RO-1", null=True, blank=True)
    lme_1 = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="LME-1", null=True, blank=True)
    po = models.CharField(max_length=100, verbose_name="PO")
    acao = models.CharField(max_length=255, verbose_name="AÇÃO")
    po_gnd = models.CharField(max_length=100, verbose_name="PO+GND")
    linha_id = models.CharField(max_length=10, verbose_name="ID", null=True, blank=True)

    def __str__(self):
        # Melhoria para facilitar a identificação no dropdown (ID - Data - Iniciativa - Valor)
        return f"#{self.id} | {self.data.strftime('%d/%m/%Y')} | {self.iniciativa} | {self.unidade_coordenacao} | R$ {self.ro_1}"

    class Meta:
        verbose_name = "Registro Financeiro"
        verbose_name_plural = "Registros Financeiros"