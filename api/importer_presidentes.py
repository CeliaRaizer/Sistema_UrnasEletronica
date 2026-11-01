"""Importa uma planilha só com os presidentes de prédio.

Colunas aceitas (nomes parecidos também funcionam):
  - Presidente (obrigatória)
  - Local de votação  e/ou  Seção   (ao menos uma, para achar o local)
  - Município (opcional; ajuda a desempatar)
O nome do local pode estar abreviado ("EEB MUNICIPAL ...") como nas abas de rotas.
"""
import datetime as dt
import re

from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from .importer import ErroImportacao, norm
from .importer_locais import _achar, _inteiro
from .models import LocalVotacao, Secao

PALAVRAS_LIGACAO = {"de", "da", "do", "das", "dos", "e"}


def _col(cab, pred):
    for i, c in enumerate(cab):
        if pred(norm(c)):
            return i
    return None


def _data(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, (int, float)) and v > 20000:
        return from_excel(v).date()
    t = str(v or "").strip()
    try:
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", t)
        if m:
            d, mo, a = (int(x) for x in m.groups())
            return dt.date(a + 2000 if a < 100 else a, mo, d)
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t)
        if m:
            return dt.date(*(int(x) for x in m.groups()))
    except ValueError:
        pass
    return None


def _hora(v):
    if isinstance(v, dt.datetime):
        return v.time().replace(second=0, microsecond=0)
    if isinstance(v, dt.time):
        return v.replace(second=0, microsecond=0)
    if isinstance(v, (int, float)) and 0 <= v < 1:  # hora digitada sem formato: fração do dia
        seg = round(v * 86400)
        return dt.time(seg // 3600 % 24, seg % 3600 // 60)
    m = re.search(r"(\d{1,2})\s*[:hH]\s*(\d{2})", str(v or ""))
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return dt.time(int(m.group(1)), int(m.group(2)))
    return None


def chave_local(nome):
    """Normaliza o nome do local para comparar (expande EEB e ignora 'de/da/do')."""
    n = re.sub(r"\beeb\b", "escola de educacao basica", norm(nome))
    return " ".join(p for p in n.split() if p not in PALAVRAS_LIGACAO)


def _achar_local(nome, municipio_nome, locais):
    """Devolve (local, motivo_do_erro)."""
    k = chave_local(nome)
    if municipio_nome:
        mk = norm(municipio_nome)
        do_mun = [l for l in locais if norm(l.municipio.nome) == mk]
        locais = do_mun or locais
    exatos = [l for l in locais if chave_local(l.nome) == k]
    if len(exatos) == 1:
        return exatos[0], None
    parecidos = [l for l in locais if k and (k in chave_local(l.nome) or chave_local(l.nome) in k)]
    if len(parecidos) == 1:
        return parecidos[0], None
    if len(exatos) + len(parecidos) > 1:
        return None, f"mais de um local combina com '{nome}'"
    return None, f"local '{nome}' não encontrado"


def importar_presidentes(arquivo):
    try:
        wb = load_workbook(arquivo, data_only=True)
    except Exception:
        raise ErroImportacao("Não foi possível ler o arquivo. Envie uma planilha .xlsx.")

    aba = None
    for ws in wb.worksheets:
        linhas = list(ws.iter_rows(values_only=True))
        if not linhas:
            continue
        cab = [str(c or "") for c in linhas[0]]
        c = {"presidente": _achar(cab, "presidente", "administrador"), "local": _achar(cab, "local"),
             "secao": _achar(cab, "sec"), "municipio": _achar(cab, "municipio", "cidade"),
             "telefone": _col(cab, lambda n: n.startswith(("telefone", "fone", "celular", "contato"))),
             "data": _col(cab, lambda n: "data" in n.split()),
             "saida": _col(cab, lambda n: "saida" in n or "partida" in n),
             "previsto": _col(cab, lambda n: ("previs" in n or "hora" in n) and ("entrega" in n or "previs" in n)
                              and not any(x in n for x in ("saida", "partida", "chegada", "data")))}
        if c["presidente"] is not None and (c["local"] is not None or c["secao"] is not None):
            aba = (linhas[1:], c)
            break
    if aba is None:
        raise ErroImportacao("Não encontrei as colunas: Presidente e (Local de votação ou Seção).")

    linhas, c = aba
    locais = list(LocalVotacao.objects.select_related("municipio"))
    if not locais:
        raise ErroImportacao("Importe antes a planilha de locais e rotas.")
    resumo = {"atualizados": 0, "sem_nome": 0, "erros": [], "avisos": [], "locais_sem_presidente": [],
              "colunas": [k for k in ("telefone", "data", "saida", "previsto") if c[k] is not None]}
    vistos = {}

    with transaction.atomic():
        for n, r in enumerate(linhas, start=2):
            if not any(r):
                continue
            pega = lambda k: str(r[c[k]] or "").strip() if c[k] is not None and c[k] < len(r) else ""
            nome = pega("presidente")[:120]
            if not nome:
                resumo["sem_nome"] += 1
                continue
            local, motivo = None, None
            if pega("local"):
                local, motivo = _achar_local(pega("local"), pega("municipio"), locais)
            if local is None and c["secao"] is not None:
                numeros = [int(x) for x in re.findall(r"\d+", str(r[c["secao"]] if c["secao"] < len(r) else ""))]
                sec = Secao.objects.select_related("local").filter(numero__in=numeros).first() if numeros else None
                if sec:
                    local, motivo = sec.local, None
                elif motivo is None:
                    motivo = f"seção '{pega('secao')}' não encontrada"
            if local is None:
                resumo["erros"].append({"linha": n, "motivo": motivo or "não consegui identificar o local"})
                continue
            if local.id in vistos and vistos[local.id] != nome:
                resumo["erros"].append({"linha": n, "motivo": f"'{local.nome}' já recebeu o presidente '{vistos[local.id]}' nesta planilha"})
                continue
            vistos[local.id] = nome
            local.presidente = nome
            campos = ["presidente"]
            if pega("telefone"):
                local.presidente_telefone = pega("telefone")[:40]
                campos.append("presidente_telefone")
            for chave, campo, conversor, rotulo in (("data", "data_entrega", _data, "data"),
                                                    ("saida", "hora_saida", _hora, "horário de saída"),
                                                    ("previsto", "hora_prevista", _hora, "horário previsto")):
                bruto = r[c[chave]] if c[chave] is not None and c[chave] < len(r) else None
                if bruto in (None, ""):
                    continue
                valor = conversor(bruto)
                if valor is None:
                    resumo["avisos"].append(f"Linha {n}: {rotulo} '{bruto}' não reconhecido(a); ignorado(a).")
                else:
                    setattr(local, campo, valor)
                    campos.append(campo)
            local.save(update_fields=campos)
            resumo["atualizados"] += 1
    resumo["locais_sem_presidente"] = list(
        LocalVotacao.objects.filter(presidente="").values_list("nome", flat=True))
    return resumo
