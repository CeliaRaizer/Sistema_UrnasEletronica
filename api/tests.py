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
        self.assertEqual((r.data["resumo"]["total"], r.data["resumo"]["entregue"], r.data["resumo"]["em_transito"]), (2, 1, 1))
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
