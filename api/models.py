from django.db import models


def normalizar_patrimonio(valor):
    """Padroniza o patrimônio (QR ou digitado): sem espaços e em maiúsculas."""
    return str(valor or "").strip().upper()


class Municipio(models.Model):
    nome = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class LocalVotacao(models.Model):
    AREAS = [("urbano", "Urbano"), ("interior", "Interior")]

    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name="locais")
    nome = models.CharField(max_length=200)
    area = models.CharField(max_length=10, choices=AREAS, default="urbano")
    bairro = models.CharField(max_length=120, blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    cep = models.CharField(max_length=10, blank=True)
    # Presidente de prédio: coordena o local inteiro e recebe todas as urnas dele.
    presidente = models.CharField(max_length=120, blank=True)
    presidente_telefone = models.CharField(max_length=40, blank=True)
    # Cronograma da entrega (vem da planilha de presidentes / Sistema de Rotas)
    data_entrega = models.DateField(null=True, blank=True)
    hora_saida = models.TimeField(null=True, blank=True)      # saída (partida) do cartório
    hora_prevista = models.TimeField(null=True, blank=True)   # chegada prevista neste local

    class Meta:
        ordering = ["municipio__nome", "nome"]
        unique_together = [("municipio", "nome")]
        verbose_name = "local de votação"
        verbose_name_plural = "locais de votação"

    def __str__(self):
        return f"{self.nome} ({self.municipio})"


class Rota(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    # Quem faz a distribuição (como no formulário "Controle de Distribuição")
    responsavel = models.CharField(max_length=200, blank=True, help_text="Ex.: Celia / Daniel José Cantelli")
    placa = models.CharField(max_length=15, blank=True)
    celular = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"Rota {self.numero}"


class Secao(models.Model):
    rota = models.ForeignKey(Rota, null=True, blank=True, on_delete=models.SET_NULL, related_name="secoes")
    local = models.ForeignKey(LocalVotacao, on_delete=models.CASCADE, related_name="secoes")
    zona = models.PositiveSmallIntegerField()
    numero = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["zona", "numero"]
        unique_together = [("zona", "numero")]
        verbose_name = "seção"
        verbose_name_plural = "seções"

    def __str__(self):
        return f"Seção {self.numero} (zona {self.zona})"


class Urna(models.Model):
    # O QR code físico da urna codifica o patrimônio, então ele é a chave de busca.
    patrimonio = models.CharField(max_length=30, unique=True)
    secao = models.ForeignKey(Secao, null=True, blank=True, on_delete=models.SET_NULL, related_name="urnas")
    # Urna de contingência não tem seção fixa; fica ligada a um município.
    contingencia = models.BooleanField(default=False)
    municipio = models.ForeignKey(Municipio, null=True, blank=True, on_delete=models.SET_NULL, related_name="urnas_contingencia")

    class Meta:
        ordering = ["patrimonio"]

    def save(self, *args, **kwargs):
        self.patrimonio = normalizar_patrimonio(self.patrimonio)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.patrimonio


class Entrega(models.Model):
    EM_TRANSITO, ENTREGUE, PENDENCIA = "em_transito", "entregue", "pendencia"
    STATUS = [(EM_TRANSITO, "Em trânsito"), (ENTREGUE, "Entregue"), (PENDENCIA, "Pendência")]

    urna = models.OneToOneField(Urna, on_delete=models.CASCADE, related_name="entrega")
    status = models.CharField(max_length=12, choices=STATUS, default=EM_TRANSITO)
    responsavel_distribuicao = models.CharField(max_length=120, blank=True)
    recebido_por = models.CharField(max_length=120, blank=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)
    # Local que a pessoa informou estar na hora de confirmar (para validar a entrega).
    local_informado = models.ForeignKey(LocalVotacao, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.urna} - {self.get_status_display()}"


class Ocorrencia(models.Model):
    TIPOS = [("atraso", "Atraso"), ("avaria", "Avaria"), ("urna_incorreta", "Urna incorreta"), ("outro", "Outro")]

    entrega = models.ForeignKey(Entrega, on_delete=models.CASCADE, related_name="ocorrencias")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descricao = models.TextField(blank=True)
    registrado_por = models.CharField(max_length=120, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name_plural = "ocorrências"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.entrega.urna}"
