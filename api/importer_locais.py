"""Importa a planilha de locais de votação + rotas (locais_votacao.xlsx).

Estrutura esperada:
  - 1ª aba (locais): Bairro, CEP, Endereço, Município, Local de votação,
    "Seções (aptas)" no formato "1(382), 2(380)", Zona eleitoral.
  - Abas "Rota N": uma por rota, com a coluna de seções (a chave de ligação).
A seção é a chave: ela diz em qual local está e em qual rota vai.
"""
import re

from django.db import transaction
from openpyxl import load_workbook

from .importer import ErroImportacao, norm
from .models import LocalVotacao, Municipio, Rota, Secao


def _achar(cabecalhos, *prefixos):
    for i, c in enumerate(cabecalhos):
        n = norm(c)
        if any(n.startswith(p) for p in prefixos):
            return i
    return None


def _inteiro(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def importar_locais_rotas(arquivo):
    try:
        wb = load_workbook(arquivo, data_only=True)
    except Exception:
        raise ErroImportacao("Não foi possível ler o arquivo. Envie uma planilha .xlsx.")

    # --- aba de locais: a primeira que tem Município, Local, Seções e Zona
    aba_locais = None
    for ws in wb.worksheets:
        linhas = list(ws.iter_rows(values_only=True))
        if not linhas:
            continue
        cab = [str(c or "") for c in linhas[0]]
        cols = {k: _achar(cab, *p) for k, p in {
            "municipio": ("municipio",), "local": ("local",), "secoes": ("secoes", "secao"),
            "zona": ("zona",), "bairro": ("bairro",), "cep": ("cep",), "endereco": ("endereco",)}.items()}
        if all(cols[k] is not None for k in ("municipio", "local", "secoes", "zona")):
            aba_locais = (linhas[1:], cols)
            break
    if aba_locais is None:
        raise ErroImportacao("Não encontrei a aba de locais (colunas Município, Local de votação, Seções e Zona).")

    municipios = {norm(m.nome): m for m in Municipio.objects.all()}
    avisos = []
    resumo = {"locais": 0, "secoes": 0, "rotas": 0, "avisos": avisos}

    with transaction.atomic():
        secoes_db = {}
        linhas, c = aba_locais
        for n, r in enumerate(linhas, start=2):
            if not any(r):
                continue
            nome_mun = str(r[c["municipio"]] or "").strip()
            municipio = municipios.get(norm(nome_mun))
            if municipio is None:
                raise ErroImportacao(f"Linha {n} da aba de locais: município desconhecido '{nome_mun}'.")
            nome_local = str(r[c["local"]] or "").strip()
            zona = _inteiro(r[c["zona"]])
            numeros = [int(x) for x in re.findall(r"(\d+)\s*(?:\(|,|$)", str(r[c["secoes"]] or ""))]
            if not nome_local or zona is None or not numeros:
                raise ErroImportacao(f"Linha {n} da aba de locais: faltam local, zona ou seções.")
            pega = lambda k: str(r[c[k]] or "").strip() if c[k] is not None else ""
            area = "interior" if re.search(r"\b(estrada|interior)\b", norm(pega("endereco"))) else "urbano"
            local, _ = LocalVotacao.objects.update_or_create(
                municipio=municipio, nome=nome_local,
                defaults={"area": area, "endereco": pega("endereco"), "bairro": pega("bairro"), "cep": pega("cep")})
            resumo["locais"] += 1
            for num in numeros:
                secoes_db[num], _ = Secao.objects.update_or_create(zona=zona, numero=num, defaults={"local": local})
                resumo["secoes"] += 1

        # --- abas de rotas
        com_rota = {}
        for ws in wb.worksheets:
            if not norm(ws.title).startswith("rota"):
                continue
            num_rota = _inteiro(re.sub(r"\D", "", ws.title))
            linhas = list(ws.iter_rows(values_only=True))
            if num_rota is None or not linhas:
                continue
            cab = [str(x or "") for x in linhas[0]]
            ci, ti = _achar(cab, "sec"), _achar(cab, "total")
            if ci is None:
                avisos.append(f"{ws.title}: coluna de seções não encontrada; aba ignorada.")
                continue
            rota, _ = Rota.objects.get_or_create(numero=num_rota)
            resumo["rotas"] += 1
            contadas, declarado = 0, None
            for r in linhas[1:]:
                if ti is not None and r[ti] not in (None, ""):
                    declarado = _inteiro(r[ti])
                num = _inteiro(r[ci]) if ci < len(r) else None
                if num is None:
                    continue
                contadas += 1
                sec = secoes_db.get(num)
                if sec is None:
                    avisos.append(f"{ws.title}: seção {num} não existe na aba de locais.")
                    continue
                if num in com_rota and com_rota[num] != num_rota:
                    avisos.append(f"Seção {num} aparece nas rotas {com_rota[num]} e {num_rota}; valeu a {num_rota}.")
                com_rota[num] = num_rota
                sec.rota = rota
                sec.save(update_fields=["rota"])
            if declarado is not None and declarado != contadas:
                avisos.append(f"{ws.title}: o total diz {declarado}, mas a aba lista {contadas} seções.")
        for num in sorted(set(secoes_db) - set(com_rota)):
            avisos.append(f"Seção {num} não está em nenhuma rota.")
    return resumo
