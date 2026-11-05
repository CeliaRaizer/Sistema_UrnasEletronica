"""Apagar dados importados pelo próprio sistema (com cópia de segurança automática)."""
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection

from .models import Entrega, LocalVotacao, Ocorrencia, Rota, Secao, Urna


def copia_de_seguranca():
    """Salva uma cópia do banco (SQLite) antes de apagar. Guarda as 10 mais recentes. Devolve o nome do arquivo."""
    if connection.vendor != "sqlite":
        return None
    pasta = Path(settings.BACKUP_DIR)
    pasta.mkdir(parents=True, exist_ok=True)
    base = f"backup-{datetime.now():%Y%m%d-%H%M%S}"
    destino, n = pasta / f"{base}.sqlite3", 2
    while destino.exists():  # duas operações no mesmo segundo não podem sobrescrever a cópia
        destino, n = pasta / f"{base}-{n}.sqlite3", n + 1
    copia = sqlite3.connect(destino)
    try:
        connection.ensure_connection()
        # exporta o banco inteiro (estrutura + dados) para o arquivo novo; não depende de trava do SQLite
        copia.executescript("\n".join(connection.connection.iterdump()))
    finally:
        copia.close()
    for antigo in sorted(pasta.glob("backup-*.sqlite3"), key=lambda f: f.stat().st_mtime)[:-10]:
        antigo.unlink(missing_ok=True)
    return destino.name


def _texto(partes):
    itens = [f"{n} {sing if n == 1 else plur}" for n, sing, plur in partes if n]
    return ", ".join(itens) if itens else "Nada para apagar"


def _limpar_presidentes(qs):
    return qs.exclude(presidente="", presidente_telefone="", data_entrega=None, hora_saida=None, hora_prevista=None)


def _apagar_urnas():
    Ocorrencia.objects.all().delete()
    Entrega.objects.all().delete()
    Urna.objects.all().delete()


def _desfazer_confirmacoes():
    Ocorrencia.objects.all().delete()
    Entrega.objects.update(status=Entrega.EM_TRANSITO, recebido_por="", confirmado_em=None, local_informado=None)


def _limpar_dados_dos_locais():
    LocalVotacao.objects.update(presidente="", presidente_telefone="", data_entrega=None, hora_saida=None, hora_prevista=None)


def _apagar_tudo():
    _apagar_urnas()
    Secao.objects.all().delete()
    Rota.objects.all().delete()
    LocalVotacao.objects.all().delete()


ESCOPOS = {
    "confirmacoes": {
        "titulo": "Confirmações e ocorrências",
        "descricao": "Desfaz as confirmações de recebimento e apaga as ocorrências. As urnas continuam cadastradas. Útil depois de um teste.",
        "contar": lambda: _texto([
            (Entrega.objects.exclude(status=Entrega.EM_TRANSITO).count(), "entrega confirmada ou com pendência", "entregas confirmadas ou com pendência"),
            (Ocorrencia.objects.count(), "ocorrência", "ocorrências")]),
        "apagar": _desfazer_confirmacoes,
    },
    "urnas": {
        "titulo": "Urnas cadastradas",
        "descricao": "Apaga as urnas vinculadas às seções, com suas entregas e ocorrências. Locais, seções e rotas continuam.",
        "contar": lambda: _texto([(Urna.objects.count(), "urna", "urnas"), (Ocorrencia.objects.count(), "ocorrência", "ocorrências")]),
        "apagar": _apagar_urnas,
    },
    "presidentes": {
        "titulo": "Presidentes, telefones e horários",
        "descricao": "Limpa o presidente, o telefone, a data e os horários de todos os locais (o que veio da planilha de presidentes).",
        "contar": lambda: _texto([(_limpar_presidentes(LocalVotacao.objects).count(), "local com dados", "locais com dados")]),
        "apagar": _limpar_dados_dos_locais,
    },
    "tudo": {
        "titulo": "Tudo da planilha de locais e rotas",
        "descricao": "Apaga locais, seções, rotas (com responsável e placa) e, junto, as urnas, entregas e ocorrências, que dependem das seções. Os municípios e os usuários continuam.",
        "contar": lambda: _texto([
            (LocalVotacao.objects.count(), "local", "locais"), (Secao.objects.count(), "seção", "seções"),
            (Rota.objects.count(), "rota", "rotas"), (Urna.objects.count(), "urna", "urnas"),
            (Ocorrencia.objects.count(), "ocorrência", "ocorrências")]),
        "apagar": _apagar_tudo,
    },
}


# ---------- Excluir uma rota ou um local ----------
from django.db import transaction  # noqa: E402


def _urnas_das(secoes):
    return Urna.objects.filter(secao__in=secoes)


def _apagar_urnas_das(secoes):
    """Apaga as urnas ligadas às seções, com entregas e ocorrências (a urna só tem SET_NULL na seção)."""
    urnas = _urnas_das(secoes)
    Ocorrencia.objects.filter(entrega__urna__in=urnas).delete()
    Entrega.objects.filter(urna__in=urnas).delete()
    urnas.delete()


def _impacto(secoes, locais):
    urnas = _urnas_das(secoes)
    return {
        "secoes": secoes.count(),
        "locais": len(locais),
        "urnas": urnas.count(),
        "ocorrencias": Ocorrencia.objects.filter(entrega__urna__in=urnas).count(),
        "confirmadas": Entrega.objects.filter(urna__in=urnas).exclude(status=Entrega.EM_TRANSITO).count(),
    }


def _locais_que_ficariam_vazios(rota):
    ids = set(Secao.objects.filter(rota=rota).values_list("local_id", flat=True))
    return [i for i in ids if not Secao.objects.filter(local_id=i).exclude(rota=rota).exists()]


def impacto_rota(rota):
    """O que acontece em cada modo de excluir a rota."""
    secoes = Secao.objects.filter(rota=rota)
    return {"numero": rota.numero, **_impacto(secoes, _locais_que_ficariam_vazios(rota))}


def excluir_rota(rota, modo):
    """modo 'so_rota': as seções ficam sem rota. modo 'tudo': apaga também as seções da rota, as urnas delas
    e os locais que ficarem sem nenhuma seção."""
    with transaction.atomic():
        if modo == "tudo":
            secoes = Secao.objects.filter(rota=rota)
            vazios = _locais_que_ficariam_vazios(rota)
            _apagar_urnas_das(secoes)
            secoes.delete()
            LocalVotacao.objects.filter(id__in=vazios).delete()
        rota.delete()


def impacto_local(local):
    return {"nome": local.nome, **_impacto(local.secoes.all(), [local.id])}


def excluir_local(local):
    """Apaga o local, as seções dele e as urnas dessas seções (com entregas e ocorrências)."""
    with transaction.atomic():
        _apagar_urnas_das(local.secoes.all())
        local.delete()
