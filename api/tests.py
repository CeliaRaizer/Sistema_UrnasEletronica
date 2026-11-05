import io

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import Entrega, LocalVotacao, Municipio, Ocorrencia, Urna

CSV = (
    "Patrimônio;Seção;Zona;Local de Votação;Responsável;Município\n"
    "2012345;12;37;Escola A;Silva;Treze Tílias\n"
    "2012346;13;37;Escola B;Silva;Treze Tílias\n"
    "2012347;14;37;Escola B;Silva;Cidade Inexistente\n"
).encode("utf-8")


class BaseTest(APITestCase):
    def setUp(self):
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        self.campo = APIClient()  # sem login
        arq = io.BytesIO(CSV)
        arq.name = "rotas.csv"
        self.resp_import = self.admin.post("/api/importar/", {"arquivo": arq}, format="multipart")


class ImportacaoTests(BaseTest):
    def test_municipios_iniciais_existem(self):
        self.assertEqual(Municipio.objects.count(), 5)

    def test_importa_validas_e_reporta_erro(self):
        self.assertEqual(self.resp_import.data["criadas"], 2)
        self.assertEqual(len(self.resp_import.data["erros"]), 1)
        self.assertEqual(self.resp_import.data["erros"][0]["linha"], 4)
        self.assertEqual(Entrega.objects.get(urna__patrimonio="2012345").responsavel_distribuicao, "Silva")

    def test_reimportar_nao_duplica(self):
        arq = io.BytesIO(CSV); arq.name = "rotas.csv"
        r = self.admin.post("/api/importar/", {"arquivo": arq}, format="multipart")
        self.assertEqual((r.data["criadas"], r.data["atualizadas"]), (0, 2))
        self.assertEqual(Urna.objects.count(), 2)

    def test_importar_exige_login(self):
        self.assertEqual(self.campo.post("/api/importar/").status_code, 401)


class CampoTests(BaseTest):
    def test_consulta_mostra_secao(self):
        r = self.campo.get("/api/urnas/consulta/", {"patrimonio": " 2012345 "})
        self.assertEqual((r.status_code, r.data["secao"], r.data["local"]["nome"]), (200, 12, "Escola A"))

    def test_consulta_inexistente(self):
        self.assertEqual(self.campo.get("/api/urnas/consulta/", {"patrimonio": "999"}).status_code, 404)

    def test_confirmar_exige_nome(self):
        self.assertEqual(self.campo.post("/api/confirmar/", {"patrimonio": "2012345"}).status_code, 400)

    def test_confirmar_ok_e_idempotente(self):
        local = LocalVotacao.objects.get(nome="Escola A")
        dados = {"patrimonio": "2012345", "nome": "Maria", "local_id": local.id}
        self.assertEqual(self.campo.post("/api/confirmar/", dados).data["resultado"], "confirmada")
        self.assertEqual(self.campo.post("/api/confirmar/", dados).data["resultado"], "ja_confirmada")
        e = Entrega.objects.get(urna__patrimonio="2012345")
        self.assertEqual((e.status, e.recebido_por), ("entregue", "Maria"))

    def test_local_errado_gera_pendencia_e_ocorrencia(self):
        errado = LocalVotacao.objects.get(nome="Escola B")
        r = self.campo.post("/api/confirmar/", {"patrimonio": "2012345", "nome": "João", "local_id": errado.id})
        self.assertEqual(r.data["resultado"], "divergente")
        self.assertEqual(Entrega.objects.get(urna__patrimonio="2012345").status, "pendencia")
        self.assertEqual(Ocorrencia.objects.filter(tipo="urna_incorreta").count(), 1)

    def test_registrar_ocorrencia(self):
        r = self.campo.post("/api/ocorrencias/", {"patrimonio": "2012345", "tipo": "avaria", "nome": "Ana"})
        self.assertEqual(r.status_code, 201)


class CartorioTests(BaseTest):
    def test_painel_exige_login(self):
        self.assertEqual(self.campo.get("/api/painel/").status_code, 401)

    def test_painel_resumo_e_filtro(self):
        self.campo.post("/api/confirmar/", {"patrimonio": "2012345", "nome": "Maria"})
        r = self.admin.get("/api/painel/")
        self.assertEqual((r.data["resumo"]["total"], r.data["resumo"]["entregue"], r.data["resumo"]["aguardando"]), (2, 1, 1))
        r = self.admin.get("/api/painel/", {"status": "entregue"})
        self.assertEqual(len(r.data["entregas"]), 1)
        self.assertEqual(r.data["entregas"][0]["recebido_por"], "Maria")

    def test_associar_manual_e_contingencia(self):
        r = self.admin.post("/api/urnas/associar/", {"patrimonio": "777", "zona": 37, "secao": 12, "substituir": True})
        self.assertEqual((r.status_code, r.data["local"]["nome"]), (201, "Escola A"))
        mun = Municipio.objects.get(nome="Ibiam")
        r = self.admin.post("/api/urnas/associar/", {"patrimonio": "888", "contingencia": True, "municipio_id": mun.id}, format="json")
        self.assertEqual((r.status_code, r.data["contingencia"], r.data["municipio"]), (201, True, "Ibiam"))


# ---------- Planilha de locais + rotas ----------
import os
from django.conf import settings
from .models import Rota, Secao

PLANILHA_REAL = os.path.join(settings.BASE_DIR, "exemplos", "locais_votacao.xlsx")


class ImportarLocaisTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)

    def enviar(self, caminho=PLANILHA_REAL):
        with open(caminho, "rb") as f:
            return self.admin.post("/api/importar-locais/", {"arquivo": f}, format="multipart")

    def test_planilha_real(self):
        r = self.enviar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["secoes"], r.data["rotas"], r.data["avisos"]), (74, 8, []))
        self.assertEqual(Secao.objects.count(), 74)
        self.assertEqual(Secao.objects.filter(rota__isnull=True).count(), 0)
        self.assertEqual(Rota.objects.get(numero=1).secoes.count(), 20)
        s51 = Secao.objects.get(zona=47, numero=51)
        self.assertEqual((s51.rota.numero, s51.local.municipio.nome), (1, "Treze Tílias"))
        self.assertEqual(Secao.objects.get(numero=55).local.area, "interior")
        self.assertEqual(Secao.objects.get(numero=1).local.area, "urbano")

    def test_reimportar_nao_duplica(self):
        self.enviar(); self.enviar()
        self.assertEqual(Secao.objects.count(), 74)

    def test_exige_login_e_arquivo(self):
        self.assertEqual(APIClient().post("/api/importar-locais/").status_code, 401)
        self.assertEqual(self.admin.post("/api/importar-locais/").status_code, 400)

    def test_secoes_e_associar_com_travas(self):
        self.enviar()
        lista = self.admin.get("/api/secoes/").data
        self.assertEqual(len(lista), 74)
        self.assertIsNone(next(x for x in lista if x["numero"] == 51)["patrimonio"])
        campos = {"endereco", "bairro", "presidente_telefone", "data_entrega", "hora_saida", "hora_prevista", "rota_responsavel", "rota_placa", "rota_celular"}
        self.assertTrue(campos <= set(lista[0]))
        # vincula, depois reaparece na lista com rota
        r = self.admin.post("/api/urnas/associar/", {"patrimonio": "100", "zona": 47, "secao": 51})
        self.assertEqual((r.status_code, r.data["rota"]), (201, 1))
        self.assertEqual(next(x for x in self.admin.get("/api/secoes/").data if x["numero"] == 51)["patrimonio"], "100")
        # mesma urna em outra seção -> 409; outra urna na mesma seção -> 409
        self.assertEqual(self.admin.post("/api/urnas/associar/", {"patrimonio": "100", "zona": 47, "secao": 52}).status_code, 409)
        self.assertEqual(self.admin.post("/api/urnas/associar/", {"patrimonio": "200", "zona": 47, "secao": 51}).status_code, 409)
        # substituir confirma a troca e solta a urna antiga
        r = self.admin.post("/api/urnas/associar/", {"patrimonio": "200", "zona": 47, "secao": 51, "substituir": True})
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(Urna.objects.get(patrimonio="100").secao)

    def test_painel_filtra_por_rota(self):
        self.enviar()
        self.admin.post("/api/urnas/associar/", {"patrimonio": "100", "zona": 47, "secao": 51})
        self.admin.post("/api/urnas/associar/", {"patrimonio": "300", "zona": 47, "secao": 1})
        r = self.admin.get("/api/painel/", {"rota": 7})
        self.assertEqual([e["patrimonio"] for e in r.data["entregas"]], ["300"])
        self.assertEqual(r.data["rotas"], list(range(1, 9)))


# ---------- Presidentes de prédio ----------
import tempfile
from openpyxl import Workbook, load_workbook as _lw
from .models import LocalVotacao


def _xlsx(linhas, nome="p.xlsx"):
    wb = Workbook(); ws = wb.active
    for l in linhas:
        ws.append(l)
    f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False); wb.save(f.name)
    return f.name


class PresidentesTests(ImportarLocaisTests):
    def enviar_para(self, caminho, rota):
        with open(caminho, "rb") as f:
            return self.admin.post(rota, {"arquivo": f}, format="multipart")

    def test_coluna_na_planilha_principal(self):
        wb = _lw(PLANILHA_REAL); ws = wb.worksheets[0]
        ws.cell(row=1, column=9, value="Presidente de prédio")
        ws.cell(row=2, column=9, value="Maria Souza")  # Pinheiro Preto
        f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False); wb.save(f.name)
        self.assertEqual(self.enviar_para(f.name, "/api/importar-locais/").status_code, 200)
        self.assertEqual(LocalVotacao.objects.get(municipio__nome="Pinheiro Preto").presidente, "Maria Souza")
        # reimportar a planilha original (sem a coluna) não apaga o nome
        self.enviar()
        self.assertEqual(LocalVotacao.objects.get(municipio__nome="Pinheiro Preto").presidente, "Maria Souza")

    def test_planilha_so_de_presidentes_com_nomes_abreviados(self):
        self.enviar()
        caminho = _xlsx([
            ["Município", "Local de votação", "Presidente"],
            ["Pinheiro Preto", "EEB PROFESSORA MAURA SENNA PEREIRA", "Maria Souza"],      # abreviado, como nas abas de rota
            ["Treze Tilias", "EEB MUNICIPAL IRMÃ FILOMENA RABELO", "João Lima"],            # sem acento no município
            ["Tangará", "PAVILHÃO DA CAPELA DE MARARI", "Ana Paula"],
            ["Tangará", "Escola Inexistente", "Fulano"],                                    # não existe
        ])
        r = self.enviar_para(caminho, "/api/importar-presidentes/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["atualizados"], 3)
        self.assertEqual(len(r.data["erros"]), 1)
        self.assertIn("Escola Inexistente", r.data["erros"][0]["motivo"])
        self.assertEqual(LocalVotacao.objects.get(nome__contains="MAURA").presidente, "Maria Souza")
        self.assertEqual(len(r.data["locais_sem_presidente"]), 14)

    def test_identifica_o_local_pela_secao(self):
        self.enviar()
        caminho = _xlsx([["Seção", "Presidente de prédio"], [55, "Pedro Alves"]])  # seção 55 = Escola Isolada Três Barras
        r = self.enviar_para(caminho, "/api/importar-presidentes/")
        self.assertEqual(r.data["atualizados"], 1)
        self.assertEqual(LocalVotacao.objects.get(nome__contains="TRÊS BARRAS").presidente, "Pedro Alves")

    def test_todos_os_nomes_das_abas_de_rota_sao_reconhecidos(self):
        """Os nomes abreviados das abas de rota (usados no dia a dia) devem achar o local."""
        self.enviar()
        wb = _lw(PLANILHA_REAL)
        nomes = set()
        for ws in wb.worksheets[1:]:
            cab = [str(c.value or "") for c in ws[1]]
            ci = next(i for i, x in enumerate(cab) if x.lower().startswith("local"))
            for r in ws.iter_rows(min_row=2, values_only=True):
                if r[ci]:
                    nomes.add(r[ci])
        caminho = _xlsx([["Local de votação", "Presidente"]] + [[n, f"Pres {i}"] for i, n in enumerate(sorted(nomes))])
        r = self.enviar_para(caminho, "/api/importar-presidentes/")
        self.assertEqual(r.data["erros"], [], r.data["erros"])

    def test_exige_login_e_colunas(self):
        self.assertEqual(APIClient().post("/api/importar-presidentes/").status_code, 401)
        self.enviar()
        r = self.enviar_para(_xlsx([["Nome", "Telefone"], ["x", "y"]]), "/api/importar-presidentes/")
        self.assertEqual(r.status_code, 400)

    def test_painel_e_secoes_mostram_o_presidente(self):
        self.enviar()
        self.enviar_para(_xlsx([["Local de votação", "Presidente"], ["EEB PROFESSORA MAURA SENNA PEREIRA", "Maria Souza"]]), "/api/importar-presidentes/")
        self.admin.post("/api/urnas/associar/", {"patrimonio": "1", "zona": 47, "secao": 1})
        self.assertEqual(self.admin.get("/api/painel/").data["entregas"][0]["presidente"], "Maria Souza")
        self.assertEqual(next(x for x in self.admin.get("/api/secoes/").data if x["numero"] == 1)["presidente"], "Maria Souza")
        # o presidente não aparece nos endpoints públicos
        self.assertNotIn("Maria Souza", str(APIClient().get("/api/urnas/consulta/", {"patrimonio": "1"}).data))


# ---------- Cronograma (data, saída, previsto) e responsável da rota ----------
import datetime as _dt
from django.utils import timezone as _tz


class CronogramaTests(PresidentesTests):
    def test_le_data_saida_previsto_telefone_em_varios_formatos(self):
        self.enviar()
        caminho = _xlsx([
            ["Administrador de prédio", "Telefone(s)", "Local de votação", "Data de entrega", "Horário de saída", "Horário previsto de entrega"],
            ["Denize Cecatto", "+554935621392", "EEB PROFESSORA MAURA SENNA PEREIRA", _dt.date(2026, 10, 24), _dt.time(14, 30), _dt.time(14, 50)],
            ["Joao Lima", "49 99999-0000", "EEB MUNICIPAL IRMÃ FILOMENA RABELO", "24/10/2026", "14h30", "15:10"],
            ["Ana Paula", None, "PAVILHÃO DA CAPELA DE MARARI", "data ruim", 0.625, "xx"],   # 0.625 = 15:00
        ])
        r = self.enviar_para(caminho, "/api/importar-presidentes/")
        self.assertEqual((r.status_code, r.data["atualizados"]), (200, 3))
        self.assertEqual(r.data["colunas"], ["telefone", "data", "saida", "previsto"])
        a = LocalVotacao.objects.get(nome__contains="MAURA")
        self.assertEqual((a.presidente, a.presidente_telefone, a.data_entrega, a.hora_saida, a.hora_prevista),
                         ("Denize Cecatto", "+554935621392", _dt.date(2026, 10, 24), _dt.time(14, 30), _dt.time(14, 50)))
        b = LocalVotacao.objects.get(nome__contains="FILOMENA")
        self.assertEqual((b.data_entrega, b.hora_saida, b.hora_prevista), (_dt.date(2026, 10, 24), _dt.time(14, 30), _dt.time(15, 10)))
        c = LocalVotacao.objects.get(nome__contains="MARARI")
        self.assertEqual((c.data_entrega, c.hora_saida, c.hora_prevista), (None, _dt.time(15, 0), None))
        self.assertEqual(len(r.data["avisos"]), 2)  # data ruim e horário "xx"

    def test_painel_mostra_cronograma_responsavel_e_atraso(self):
        self.enviar()
        rota = Rota.objects.get(numero=7)
        rota.responsavel, rota.placa = "Celia / Daniel", "BCI8G97"; rota.save()
        agora = _tz.localtime()
        previsto = agora - _dt.timedelta(minutes=20)
        LocalVotacao.objects.filter(nome__contains="MAURA").update(
            data_entrega=previsto.date(), hora_prevista=previsto.time().replace(second=0, microsecond=0), hora_saida=_dt.time(14, 30))
        self.admin.post("/api/urnas/associar/", {"patrimonio": "1", "zona": 47, "secao": 1})
        APIClient().post("/api/confirmar/", {"patrimonio": "1", "nome": "Denize"})
        e = self.admin.get("/api/painel/").data["entregas"][0]
        self.assertEqual((e["responsavel_distribuicao"], e["placa"], e["hora_saida"]), ("Celia / Daniel", "BCI8G97", "14:30"))
        self.assertIn(e["atraso_min"], range(19, 22))

    def test_coluna_administrador_na_planilha_principal(self):
        wb = _lw(PLANILHA_REAL); ws = wb.worksheets[0]
        ws.cell(row=1, column=9, value="Administrador de prédio"); ws.cell(row=2, column=9, value="Denize")
        f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False); wb.save(f.name)
        self.enviar_para(f.name, "/api/importar-locais/")
        self.assertEqual(LocalVotacao.objects.get(municipio__nome="Pinheiro Preto").presidente, "Denize")


# ---------- Edição de local e de rota pelo sistema ----------
class EdicaoTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        with open(PLANILHA_REAL, "rb") as f:
            self.admin.post("/api/importar-locais/", {"arquivo": f}, format="multipart")
        self.local = LocalVotacao.objects.get(nome__contains="MAURA")

    def patch(self, dados, id=None):
        return self.admin.patch(f"/api/locais/{id or self.local.id}/", dados, format="json")

    def test_edita_presidente_telefone_e_horarios(self):
        r = self.patch({"presidente": "Denize Cecatto", "presidente_telefone": "+55 49 3562-1392",
                        "data_entrega": "2026-10-24", "hora_saida": "14:30", "hora_prevista": "14:50"})
        self.assertEqual((r.status_code, r.data["hora_prevista"], r.data["data_entrega"]), (200, "14:50", "2026-10-24"))
        self.local.refresh_from_db()
        self.assertEqual((self.local.presidente, self.local.hora_saida), ("Denize Cecatto", _dt.time(14, 30)))

    def test_so_muda_o_que_foi_enviado_e_vazio_limpa(self):
        self.patch({"presidente": "Maria", "hora_prevista": "14:50"})
        self.patch({"presidente_telefone": "123"})
        self.local.refresh_from_db()
        self.assertEqual((self.local.presidente, self.local.hora_prevista), ("Maria", _dt.time(14, 50)))
        self.patch({"hora_prevista": "", "presidente": ""})
        self.local.refresh_from_db()
        self.assertEqual((self.local.presidente, self.local.hora_prevista, self.local.presidente_telefone), ("", None, "123"))

    def test_valores_invalidos_e_acesso(self):
        for dados in ({"hora_saida": "25:99"}, {"hora_prevista": "tarde"}, {"data_entrega": "2026-13-45"}, {"data_entrega": "ontem"}):
            self.assertEqual(self.patch(dados).status_code, 400, dados)
        self.assertEqual(self.patch({"presidente": "x"}, id=99999).status_code, 404)
        self.assertEqual(APIClient().patch(f"/api/locais/{self.local.id}/", {"presidente": "x"}, format="json").status_code, 401)

    def test_edicao_aparece_no_painel_e_nas_secoes(self):
        self.patch({"presidente": "Denize", "hora_prevista": "14:50", "data_entrega": "2026-10-24"})
        self.admin.post("/api/urnas/associar/", {"patrimonio": "1", "zona": 47, "secao": 1})
        e = self.admin.get("/api/painel/").data["entregas"][0]
        self.assertEqual((e["presidente"], e["hora_prevista"]), ("Denize", "14:50"))
        self.assertEqual(next(x for x in self.admin.get("/api/secoes/").data if x["numero"] == 1)["presidente"], "Denize")

    def test_edita_responsavel_da_rota(self):
        r = self.admin.patch("/api/rotas/7/", {"responsavel": "Celia / Daniel", "placa": "BCI8G97", "celular": "49 93300-1500"}, format="json")
        self.assertEqual((r.status_code, r.data["placa"]), (200, "BCI8G97"))
        self.assertEqual(Rota.objects.get(numero=7).responsavel, "Celia / Daniel")
        self.assertEqual(self.admin.patch("/api/rotas/99/", {"placa": "x"}, format="json").status_code, 404)
        self.admin.patch("/api/rotas/7/", {"responsavel": "Outro"}, format="json")
        self.assertEqual(Rota.objects.get(numero=7).placa, "BCI8G97")  # campo não enviado fica igual


# ---------- Situação por horário de saída e apagar dados ----------
import shutil
from django.test import override_settings


class SituacaoTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        with open(PLANILHA_REAL, "rb") as f:
            self.admin.post("/api/importar-locais/", {"arquivo": f}, format="multipart")
        for pat, sec in (("A1", 1), ("B1", 20), ("C1", 55)):
            self.admin.post("/api/urnas/associar/", {"patrimonio": pat, "zona": 47, "secao": sec})

    def agendar(self, trecho, dia, hora="08:00"):
        LocalVotacao.objects.filter(nome__contains=trecho).update(
            data_entrega=dia, hora_saida=_dt.time.fromisoformat(hora))

    def situacoes(self, **filtros):
        return {e["patrimonio"]: e["status"] for e in self.admin.get("/api/painel/", filtros).data["entregas"]}

    def test_sem_horario_ou_antes_da_saida_fica_aguardando(self):
        hoje = _tz.localdate()
        self.agendar("MAURA", hoje + _dt.timedelta(days=1))   # saída amanhã
        # B1 (Heriberto): sem data/horário definidos
        self.assertEqual(self.situacoes(), {"A1": "aguardando", "B1": "aguardando", "C1": "aguardando"})

    def test_depois_da_saida_vira_em_transito(self):
        hoje = _tz.localdate()
        self.agendar("MAURA", hoje - _dt.timedelta(days=1))   # saiu ontem
        s = self.situacoes()
        self.assertEqual((s["A1"], s["B1"]), ("em_transito", "aguardando"))

    def test_data_sem_horario_de_saida_nao_inicia(self):
        LocalVotacao.objects.filter(nome__contains="MAURA").update(data_entrega=_tz.localdate() - _dt.timedelta(days=1), hora_saida=None)
        self.assertEqual(self.situacoes()["A1"], "aguardando")

    def test_confirmada_fica_entregue_mesmo_antes_da_saida(self):
        self.agendar("MAURA", _tz.localdate() + _dt.timedelta(days=1))
        APIClient().post("/api/confirmar/", {"patrimonio": "A1", "nome": "Denize"})
        self.assertEqual(self.situacoes()["A1"], "entregue")

    def test_resumo_e_filtro_usam_a_situacao_calculada(self):
        self.agendar("MAURA", _tz.localdate() - _dt.timedelta(days=1))
        r = self.admin.get("/api/painel/").data["resumo"]
        self.assertEqual((r["total"], r["em_transito"], r["aguardando"], r["entregue"], r["pendencia"]), (3, 1, 2, 0, 0))
        self.assertEqual(list(self.situacoes(status="em_transito")), ["A1"])
        self.assertEqual(sorted(self.situacoes(status="aguardando")), ["B1", "C1"])
        self.assertEqual(self.admin.get("/api/painel/", {"status": "aguardando"}).data["resumo"]["total"], 3)  # resumo não muda com o filtro


class ApagarDadosTests(APITestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        with open(PLANILHA_REAL, "rb") as f:
            self.admin.post("/api/importar-locais/", {"arquivo": f}, format="multipart")
        LocalVotacao.objects.filter(nome__contains="MAURA").update(presidente="Denize", presidente_telefone="1", hora_saida=_dt.time(8, 0))
        Rota.objects.filter(numero=7).update(responsavel="Celia")
        self.admin.post("/api/urnas/associar/", {"patrimonio": "A1", "zona": 47, "secao": 1})
        APIClient().post("/api/confirmar/", {"patrimonio": "A1", "nome": "Denize"})
        APIClient().post("/api/ocorrencias/", {"patrimonio": "A1", "tipo": "avaria"})

    def apagar(self, escopo, confirmacao="APAGAR"):
        with override_settings(BACKUP_DIR=self.pasta):
            return self.admin.post("/api/apagar-dados/", {"escopo": escopo, "confirmacao": confirmacao}, format="json")

    def test_lista_o_que_cada_opcao_apagaria(self):
        r = self.admin.get("/api/apagar-dados/")
        d = {x["id"]: x["resumo"] for x in r.data}
        self.assertEqual(set(d), {"confirmacoes", "urnas", "presidentes", "tudo"})
        self.assertIn("1 urna", d["urnas"]); self.assertIn("74 seções", d["tudo"]); self.assertIn("1 local com dados", d["presidentes"])

    def test_exige_login_e_confirmacao(self):
        self.assertEqual(APIClient().get("/api/apagar-dados/").status_code, 401)
        self.assertEqual(APIClient().post("/api/apagar-dados/", {"escopo": "tudo", "confirmacao": "APAGAR"}, format="json").status_code, 401)
        self.assertEqual(self.apagar("tudo", confirmacao="").status_code, 400)
        self.assertEqual(self.apagar("tudo", confirmacao="sim").status_code, 400)
        self.assertEqual(self.apagar("inexistente").status_code, 400)
        self.assertEqual((Urna.objects.count(), Secao.objects.count()), (1, 74))   # nada foi apagado
        self.assertEqual(len(os.listdir(self.pasta)), 0)                              # nem backup

    def test_confirmacoes_desfaz_mas_mantem_urnas(self):
        r = self.apagar("confirmacoes")
        self.assertEqual(r.status_code, 200)
        e = Entrega.objects.get()
        self.assertEqual((e.status, e.recebido_por, e.confirmado_em, Ocorrencia.objects.count(), Urna.objects.count()), ("em_transito", "", None, 0, 1))

    def test_urnas_apaga_urnas_e_mantem_locais(self):
        self.apagar("urnas")
        self.assertEqual((Urna.objects.count(), Entrega.objects.count(), Ocorrencia.objects.count(), Secao.objects.count(), LocalVotacao.objects.count()), (0, 0, 0, 74, 17))

    def test_presidentes_limpa_so_os_dados_dos_locais(self):
        self.apagar("presidentes")
        l = LocalVotacao.objects.get(nome__contains="MAURA")
        self.assertEqual((l.presidente, l.presidente_telefone, l.hora_saida), ("", "", None))
        self.assertEqual((Urna.objects.count(), Rota.objects.get(numero=7).responsavel), (1, "Celia"))

    def test_tudo_apaga_planilha_mas_preserva_municipios_e_usuarios(self):
        r = self.apagar("tudo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([Urna.objects.count(), Entrega.objects.count(), Ocorrencia.objects.count(), Secao.objects.count(), Rota.objects.count(), LocalVotacao.objects.count()], [0] * 6)
        self.assertEqual((Municipio.objects.count(), User.objects.count()), (5, 1))

    def test_faz_copia_de_seguranca_antes_de_apagar(self):
        r = self.apagar("tudo")
        arquivos = os.listdir(self.pasta)
        self.assertEqual(arquivos, [r.data["backup"]])
        import sqlite3
        c = sqlite3.connect(os.path.join(self.pasta, arquivos[0]))
        self.assertEqual(c.execute("select count(*) from api_secao").fetchone()[0], 74)   # a cópia ainda tem os dados
        c.close()

    def test_duas_operacoes_seguidas_geram_copias_diferentes(self):
        a = self.apagar("confirmacoes").data["backup"]
        b = self.apagar("confirmacoes").data["backup"]
        self.assertNotEqual(a, b)
        self.assertEqual(len(os.listdir(self.pasta)), 2)


# ---------- Excluir rota e excluir local ----------
class ExcluirRotaLocalTests(APITestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        user = User.objects.create_user("cartorio", password="x")
        self.admin = APIClient()
        self.admin.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        with open(PLANILHA_REAL, "rb") as f:
            self.admin.post("/api/importar-locais/", {"arquivo": f}, format="multipart")
        for pat, sec in (("A1", 1), ("A2", 2), ("B1", 20)):   # 1 e 2: rota 7 (Maura); 20: rota 6 (Heriberto)
            self.admin.post("/api/urnas/associar/", {"patrimonio": pat, "zona": 47, "secao": sec})
        APIClient().post("/api/confirmar/", {"patrimonio": "A1", "nome": "Denize"})
        APIClient().post("/api/ocorrencias/", {"patrimonio": "A1", "tipo": "avaria"})

    def post(self, caminho, dados=None):
        with override_settings(BACKUP_DIR=self.pasta):
            return self.admin.post(caminho, dados or {}, format="json")

    def test_impacto_da_rota(self):
        d = self.admin.get("/api/rotas/7/impacto/").data
        self.assertEqual((d["secoes"], d["locais"], d["urnas"], d["ocorrencias"], d["confirmadas"]), (8, 1, 2, 1, 1))
        self.assertEqual(self.admin.get("/api/rotas/99/impacto/").status_code, 404)

    def test_so_a_rota_deixa_secoes_sem_rota_e_mantem_urnas(self):
        r = self.post("/api/rotas/7/excluir/", {"modo": "so_rota", "confirmacao": "APAGAR"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Rota.objects.filter(numero=7).exists())
        self.assertEqual((Secao.objects.count(), Secao.objects.filter(rota__isnull=True).count(), LocalVotacao.objects.count(), Urna.objects.count()), (74, 8, 17, 3))

    def test_rota_e_tudo_dela_preserva_as_outras_rotas(self):
        r = self.post("/api/rotas/7/excluir/", {"modo": "tudo", "confirmacao": "APAGAR"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((Secao.objects.count(), LocalVotacao.objects.count(), Rota.objects.count()), (66, 16, 7))
        self.assertEqual(list(Urna.objects.values_list("patrimonio", flat=True)), ["B1"])
        self.assertEqual((Entrega.objects.count(), Ocorrencia.objects.count()), (1, 0))

    def test_local_com_secoes_em_outra_rota_nao_e_apagado(self):
        Secao.objects.filter(zona=47, numero=5).update(rota=Rota.objects.get(numero=1))   # seção 5 da Maura vai para a rota 1
        self.assertEqual(self.admin.get("/api/rotas/7/impacto/").data["locais"], 0)
        self.post("/api/rotas/7/excluir/", {"modo": "tudo", "confirmacao": "APAGAR"})
        self.assertTrue(LocalVotacao.objects.filter(nome__contains="MAURA").exists())
        self.assertEqual(Secao.objects.filter(local__nome__contains="MAURA").count(), 1)     # só a 5 sobrou
        self.assertEqual(Secao.objects.count(), 67)

    def test_exige_confirmacao_modo_valido_e_login(self):
        self.assertEqual(self.post("/api/rotas/7/excluir/", {"modo": "tudo"}).status_code, 400)
        self.assertEqual(self.post("/api/rotas/7/excluir/", {"modo": "tudo", "confirmacao": "sim"}).status_code, 400)
        self.assertEqual(self.post("/api/rotas/7/excluir/", {"modo": "outro", "confirmacao": "APAGAR"}).status_code, 400)
        self.assertEqual(self.post("/api/rotas/99/excluir/", {"modo": "tudo", "confirmacao": "APAGAR"}).status_code, 404)
        self.assertEqual(APIClient().post("/api/rotas/7/excluir/", {"modo": "tudo", "confirmacao": "APAGAR"}, format="json").status_code, 401)
        self.assertEqual((Rota.objects.count(), Secao.objects.count(), len(os.listdir(self.pasta))), (8, 74, 0))

    def test_excluir_local_apaga_secoes_e_urnas_dele(self):
        local = LocalVotacao.objects.get(nome__contains="MAURA")
        d = self.admin.get(f"/api/locais/{local.id}/impacto/").data
        self.assertEqual((d["secoes"], d["urnas"]), (8, 2))
        self.assertEqual(self.post(f"/api/locais/{local.id}/excluir/", {"confirmacao": "x"}).status_code, 400)
        r = self.post(f"/api/locais/{local.id}/excluir/", {"confirmacao": "APAGAR"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((LocalVotacao.objects.count(), Secao.objects.count(), list(Urna.objects.values_list("patrimonio", flat=True))), (16, 66, ["B1"]))

    def test_faz_copia_de_seguranca(self):
        r = self.post("/api/rotas/7/excluir/", {"modo": "so_rota", "confirmacao": "APAGAR"})
        self.assertEqual(os.listdir(self.pasta), [r.data["backup"]])
