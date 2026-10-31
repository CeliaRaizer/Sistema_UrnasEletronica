from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .importer import ErroImportacao, importar
from .importer_locais import importar_locais_rotas
from .models import (Entrega, LocalVotacao, Municipio, Ocorrencia, Rota, Secao, Urna,
                     normalizar_patrimonio)


def erro(msg, status=400):
    return Response({"detail": msg}, status=status)


def dados_urna(urna):
    sec = urna.secao
    entrega = getattr(urna, "entrega", None)
    return {
        "patrimonio": urna.patrimonio,
        "contingencia": urna.contingencia,
        "secao": sec.numero if sec else None,
        "zona": sec.zona if sec else None,
        "rota": sec.rota.numero if sec and sec.rota else None,
        "local": {"id": sec.local_id, "nome": sec.local.nome} if sec else None,
        "municipio": (sec.local.municipio.nome if sec else (urna.municipio.nome if urna.municipio else None)),
        "status": entrega.status if entrega else None,
        "recebido_por": entrega.recebido_por if entrega else "",
    }


def buscar_urna(patrimonio):
    return (Urna.objects.select_related("secao__local__municipio", "secao__rota", "municipio", "entrega")
            .filter(patrimonio=normalizar_patrimonio(patrimonio)).first())


# ---------- Campo (sem login: acesso por link/QR genérico) ----------

class PublicoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []          # não exige token
    throttle_classes = [AnonRateThrottle]


class LocaisView(PublicoView):
    """GET /api/locais/ -- municípios e locais, para a pessoa escolher onde está."""
    def get(self, request):
        return Response([
            {"id": m.id, "nome": m.nome,
             "locais": [{"id": l.id, "nome": l.nome} for l in m.locais.all()]}
            for m in Municipio.objects.prefetch_related("locais")
        ])


class ConsultaUrnaView(PublicoView):
    """GET /api/urnas/consulta/?patrimonio=XXX -- mostra a seção/local da urna."""
    def get(self, request):
        urna = buscar_urna(request.query_params.get("patrimonio"))
        if urna is None:
            return erro("Urna não encontrada.", 404)
        return Response(dados_urna(urna))


class ConfirmarEntregaView(PublicoView):
    """
    POST /api/confirmar/  { patrimonio, nome, local_id?, confirmado_em? }
    - Se local_id for informado e a urna pertencer a outro local -> PENDÊNCIA
      (com ocorrência automática). Sem local_id, confirma direto.
    - Idempotente: reenviar uma urna já entregue não duplica nada (sincronização offline).
    - confirmado_em permite enviar o horário real da confirmação feita offline.
    """
    def post(self, request):
        nome = str(request.data.get("nome", "")).strip()[:120]
        if not nome:
            return erro("Informe o nome de quem está recebendo.")
        urna = buscar_urna(request.data.get("patrimonio"))
        if urna is None:
            return erro("Urna não encontrada.", 404)

        entrega, _ = Entrega.objects.get_or_create(urna=urna)
        if entrega.status == Entrega.ENTREGUE:
            return Response({"resultado": "ja_confirmada", **dados_urna(urna)})

        quando = parse_datetime(str(request.data.get("confirmado_em") or ""))
        agora = timezone.now()
        if quando is None or quando > agora:
            quando = agora
        elif timezone.is_naive(quando):
            quando = timezone.make_aware(quando)

        local_id = request.data.get("local_id")
        local = LocalVotacao.objects.filter(pk=local_id).first() if local_id else None
        divergente = bool(local and urna.secao and urna.secao.local_id != local.id)

        entrega.recebido_por, entrega.confirmado_em, entrega.local_informado = nome, quando, local
        if divergente:
            entrega.status = Entrega.PENDENCIA
            Ocorrencia.objects.create(
                entrega=entrega, tipo="urna_incorreta", registrado_por=nome,
                descricao=f"Urna lida em '{local.nome}', mas pertence a '{urna.secao.local.nome}'.")
        else:
            entrega.status = Entrega.ENTREGUE
        entrega.save()
        urna.refresh_from_db()
        return Response({"resultado": "divergente" if divergente else "confirmada", **dados_urna(urna)})


class OcorrenciaView(PublicoView):
    """POST /api/ocorrencias/ { patrimonio, tipo, descricao?, nome? }"""
    def post(self, request):
        urna = buscar_urna(request.data.get("patrimonio"))
        if urna is None:
            return erro("Urna não encontrada.", 404)
        tipo = request.data.get("tipo")
        if tipo not in dict(Ocorrencia.TIPOS):
            return erro("Tipo de ocorrência inválido.")
        entrega, _ = Entrega.objects.get_or_create(urna=urna)
        Ocorrencia.objects.create(
            entrega=entrega, tipo=tipo,
            descricao=str(request.data.get("descricao", ""))[:1000],
            registrado_por=str(request.data.get("nome", ""))[:120])
        return Response({"detail": "Ocorrência registrada."}, status=201)


# ---------- Cartório (exige login) ----------

class PainelView(APIView):
    """GET /api/painel/?municipio=<id>&local=<id>&status=<status>"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Entrega.objects.select_related("urna__secao__local__municipio", "urna__secao__rota", "urna__municipio")
        p = request.query_params
        if p.get("municipio"):
            qs = qs.filter(Q(urna__secao__local__municipio_id=p["municipio"]) | Q(urna__municipio_id=p["municipio"]))
        if p.get("local"):
            qs = qs.filter(urna__secao__local_id=p["local"])
        if p.get("rota"):
            qs = qs.filter(urna__secao__rota__numero=p["rota"])
        resumo = qs.aggregate(
            total=Count("id"),
            entregue=Count("id", filter=Q(status=Entrega.ENTREGUE)),
            em_transito=Count("id", filter=Q(status=Entrega.EM_TRANSITO)),
            pendencia=Count("id", filter=Q(status=Entrega.PENDENCIA)),
        )
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        return Response({
            "resumo": resumo,
            "rotas": list(Rota.objects.values_list("numero", flat=True)),
            "entregas": [{
                **dados_urna(e.urna),
                "responsavel_distribuicao": e.responsavel_distribuicao,
                "confirmado_em": e.confirmado_em,
                "ocorrencias": e.ocorrencias.count(),
            } for e in qs.order_by("urna__patrimonio")],
        })


class OcorrenciasListaView(APIView):
    """GET /api/ocorrencias/lista/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{
            "id": o.id, "patrimonio": o.entrega.urna.patrimonio, "tipo": o.get_tipo_display(),
            "descricao": o.descricao, "registrado_por": o.registrado_por, "criado_em": o.criado_em,
        } for o in Ocorrencia.objects.select_related("entrega__urna")])


class ImportarPlanilhaView(APIView):
    """POST /api/importar/ (multipart: arquivo, municipio?)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if arquivo is None:
            return erro("Envie o arquivo no campo 'arquivo'.")
        padrao = Municipio.objects.filter(pk=request.data.get("municipio")).first() if request.data.get("municipio") else None
        try:
            return Response(importar(arquivo, arquivo.name, padrao))
        except ErroImportacao as e:
            return erro(str(e))


class ImportarLocaisView(APIView):
    """POST /api/importar-locais/ (multipart: arquivo) -- planilha de locais + rotas."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if arquivo is None:
            return erro("Envie o arquivo no campo 'arquivo'.")
        try:
            return Response(importar_locais_rotas(arquivo))
        except ErroImportacao as e:
            return erro(str(e))


class SecoesView(APIView):
    """GET /api/secoes/ -- todas as seções com local, município, rota e urna vinculada."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Secao.objects.select_related("local__municipio", "rota").prefetch_related("urnas") \
            .order_by("local__municipio__nome", "zona", "numero")
        return Response([{
            "id": x.id, "zona": x.zona, "numero": x.numero,
            "local": x.local.nome, "local_id": x.local_id, "area": x.local.area,
            "municipio": x.local.municipio.nome, "municipio_id": x.local.municipio_id,
            "rota": x.rota.numero if x.rota else None,
            "patrimonio": next((u.patrimonio for u in x.urnas.all()), None),
        } for x in qs])


class AssociarUrnaView(APIView):
    """
    POST /api/urnas/associar/ -- carga das urnas (US04) e contingência (US06).
      { patrimonio, zona, secao, substituir? }           -> vincula à seção
      { patrimonio, contingencia: true, municipio_id }   -> urna de contingência
    Devolve 409 se a urna já está em outra seção ou a seção já tem outra urna;
    reenviar com substituir=true confirma a troca.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patrimonio = normalizar_patrimonio(request.data.get("patrimonio"))
        if not patrimonio:
            return erro("Informe o patrimônio.")
        if request.data.get("contingencia"):
            municipio = Municipio.objects.filter(pk=request.data.get("municipio_id")).first()
            if municipio is None:
                return erro("Informe um município válido para a urna de contingência.")
            valores = {"secao": None, "contingencia": True, "municipio": municipio}
        else:
            try:
                secao = Secao.objects.select_related("local").get(
                    zona=int(request.data.get("zona")), numero=int(request.data.get("secao")))
            except (Secao.DoesNotExist, TypeError, ValueError):
                return erro("Seção não encontrada (confira zona e número).", 404)
            substituir = str(request.data.get("substituir")).lower() in ("true", "1")
            existente = Urna.objects.select_related("secao").filter(patrimonio=patrimonio).first()
            if not substituir:
                if existente and existente.secao_id and existente.secao_id != secao.id:
                    return erro(f"A urna {patrimonio} já está vinculada à seção {existente.secao.numero}.", 409)
                outra = secao.urnas.exclude(patrimonio=patrimonio).first()
                if outra:
                    return erro(f"A seção {secao.numero} já tem a urna {outra.patrimonio}.", 409)
            else:  # solta as outras urnas da seção (e suas entregas ainda não confirmadas)
                for u in secao.urnas.exclude(patrimonio=patrimonio):
                    Entrega.objects.filter(urna=u, status=Entrega.EM_TRANSITO).delete()
                    u.secao = None
                    u.save(update_fields=["secao"])
            valores = {"secao": secao, "contingencia": False, "municipio": None}
        urna, criada = Urna.objects.update_or_create(patrimonio=patrimonio, defaults=valores)
        Entrega.objects.get_or_create(urna=urna)
        return Response(dados_urna(buscar_urna(patrimonio)), status=201 if criada else 200)
