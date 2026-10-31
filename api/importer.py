"""Importação da planilha de rotas exportada do Sistema Rotas (.csv ou .xlsx).

Os nomes de coluna aceitos ficam em COLUNAS; se a planilha real usar outros
nomes, basta acrescentar sinônimos ali (sem acento, minúsculo).
"""
import csv
import io
import re
import unicodedata

from django.db import transaction
from openpyxl import load_workbook

from .models import Municipio, LocalVotacao, Secao, Urna, Entrega, normalizar_patrimonio

COLUNAS = {
    "patrimonio": ["patrimonio", "patrimonio da urna", "numero patrimonio", "n patrimonio", "urna"],
    "secao": ["secao", "secao eleitoral", "numero secao", "n secao"],
    "zona": ["zona", "zona eleitoral"],
    "local": ["local de votacao", "local votacao", "local", "nome do local"],
    "responsavel": ["responsavel", "responsavel distribuicao", "responsavel pela distribuicao", "transportador", "motorista"],
    "municipio": ["municipio", "cidade"],
}
OBRIGATORIAS = ["patrimonio", "secao", "zona", "local"]


class ErroImportacao(Exception):
    pass


def norm(texto):
    texto = re.sub(r"[ºª°]", "", str(texto or ""))  # "Nº" -> "N"
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def ler_linhas(arquivo, nome):
    """Devolve (cabecalhos, linhas) onde cada linha é uma lista de valores."""
    if nome.lower().endswith((".xlsx", ".xlsm")):
        ws = load_workbook(arquivo, read_only=True, data_only=True).active
        linhas = [list(r) for r in ws.iter_rows(values_only=True)]
    elif nome.lower().endswith(".csv"):
        bruto = arquivo.read()
        try:
            texto = bruto.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = bruto.decode("latin-1")
        try:
            dialeto = csv.Sniffer().sniff(texto[:2000], delimiters=";,\t")
        except csv.Error:
            dialeto = csv.excel
        linhas = list(csv.reader(io.StringIO(texto), dialeto))
    else:
        raise ErroImportacao("Formato não suportado. Envie um arquivo .xlsx ou .csv.")
    linhas = [l for l in linhas if any(str(c or "").strip() for c in l)]
    if not linhas:
        raise ErroImportacao("A planilha está vazia.")
    return linhas[0], linhas[1:]


def mapear(cabecalhos):
    achados = {}
    for i, cab in enumerate(cabecalhos):
        for campo, sinonimos in COLUNAS.items():
            if campo not in achados and norm(cab) in sinonimos:
                achados[campo] = i
    return achados


def inteiro(valor):
    return int(float(str(valor).strip().replace(",", ".")))


def importar(arquivo, nome, municipio_padrao=None):
    cabecalhos, linhas = ler_linhas(arquivo, nome)
    cols = mapear(cabecalhos)
    faltando = [c for c in OBRIGATORIAS if c not in cols]
    if "municipio" not in cols and municipio_padrao is None:
        faltando.append("municipio (ou escolha o município no envio)")
    if faltando:
        raise ErroImportacao("Colunas não encontradas: " + ", ".join(faltando))

    municipios = {norm(m.nome): m for m in Municipio.objects.all()}
    resumo = {"criadas": 0, "atualizadas": 0, "erros": []}

    def celula(linha, campo):
        i = cols.get(campo)
        return linha[i] if i is not None and i < len(linha) else ""

    with transaction.atomic():
        for n, linha in enumerate(linhas, start=2):  # linha 1 = cabeçalho
            try:
                patrimonio = normalizar_patrimonio(celula(linha, "patrimonio"))
                if not patrimonio:
                    raise ValueError("patrimônio vazio")
                zona, secao = inteiro(celula(linha, "zona")), inteiro(celula(linha, "secao"))
                nome_local = str(celula(linha, "local")).strip()
                if not nome_local:
                    raise ValueError("local de votação vazio")
                if "municipio" in cols and str(celula(linha, "municipio")).strip():
                    municipio = municipios.get(norm(celula(linha, "municipio")))
                    if municipio is None:
                        raise ValueError(f"município desconhecido: {celula(linha, 'municipio')}")
                else:
                    municipio = municipio_padrao
            except (ValueError, TypeError) as e:
                resumo["erros"].append({"linha": n, "motivo": str(e)})
                continue

            local, _ = LocalVotacao.objects.get_or_create(municipio=municipio, nome=nome_local)
            sec, _ = Secao.objects.update_or_create(zona=zona, numero=secao, defaults={"local": local})
            urna, criada = Urna.objects.update_or_create(
                patrimonio=patrimonio, defaults={"secao": sec, "contingencia": False})
            responsavel = str(celula(linha, "responsavel")).strip()
            entrega, _ = Entrega.objects.get_or_create(urna=urna, defaults={"responsavel_distribuicao": responsavel})
            if entrega.status != Entrega.ENTREGUE and responsavel:
                entrega.responsavel_distribuicao = responsavel
                entrega.save(update_fields=["responsavel_distribuicao"])
            resumo["criadas" if criada else "atualizadas"] += 1
    return resumo
