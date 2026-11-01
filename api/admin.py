from django.contrib import admin
from .models import Municipio, LocalVotacao, Rota, Secao, Urna, Entrega, Ocorrencia


@admin.register(LocalVotacao)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nome", "municipio", "area", "presidente", "data_entrega", "hora_saida", "hora_prevista")
    list_filter = ("municipio", "area")
    search_fields = ("nome",)


@admin.register(Secao)
class SecaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "zona", "local", "rota")
    list_filter = ("local__municipio", "rota")


@admin.register(Urna)
class UrnaAdmin(admin.ModelAdmin):
    list_display = ("patrimonio", "secao", "contingencia", "municipio")
    list_filter = ("contingencia",)
    search_fields = ("patrimonio",)


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("urna", "status", "responsavel_distribuicao", "recebido_por", "confirmado_em")
    list_filter = ("status",)


admin.site.register(Municipio)
@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):
    list_display = ("numero", "responsavel", "placa", "celular")

admin.site.register(Ocorrencia)
