from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .importer import ErroImportacao, importar
from .importer_locais import importar_locais_rotas
from .importer_presidentes import importar_presidentes
from .manutencao import (ESCOPOS, copia_de_seguranca, excluir_local, excluir_rota,
                         impacto_local, impacto_rota)
from .models import (Entrega, LocalVotacao, Municipio, Ocorrencia, Rota, Secao, Urna,
                     normalizar_patrimonio)


def _hm(t):
    return t.strftime("%H:%M") if t else None


def _atraso_min(entrega, local):
    """Minutos entre o horário previsto e a confirmação (positivo = atrasou)."""
    if not (entrega.confirmado_em and local and local.data_entrega and local.hora_prevista):
        return None
    previsto = timezone.make_aware(datetime.combine(local.data_entrega, local.hora_prevista))
    return round((entrega.confirmado_em - previsto).total_seconds() / 60)


AGUARDANDO = "aguardando"


def situacao(entrega, local, agora):
    """
    Situação mostrada no painel. "Entregue" e "pendência" vêm do banco. Antes de a urna ser
    confirmada, ela só está "em trânsito" a partir da data e do horário de saída previstos do local;
    antes disso (ou sem data/horário de saída definidos) fica "aguardando" a saída.
    """
    if entrega.status in (Entrega.ENTREGUE, Entrega.PENDENCIA):
        return entrega.status
    if local and local.data_entrega and local.hora_saida:
        saida = timezone.make_aware(datetime.combine(local.data_entrega, local.hora_saida))
        if agora >= saida:
            return Entrega.EM_TRANSITO
    return AGUARDANDO


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
    """GET /api/painel/?municipio=<id>&local=<id>&rota=<n>&status=<aguardando|em_transito|entregue|pendencia>"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (Entrega.objects
              .select_related("urna__secao__local__municipio", "urna__secao__rota", "urna__municipio")
              .prefetch_related("ocorrencias"))
        p = request.query_params
        if p.get("municipio"):
            qs = qs.filter(Q(urna__secao__local__municipio_id=p["municipio"]) | Q(urna__municipio_id=p["municipio"]))
        if p.get("local"):
            qs = qs.filter(urna__secao__local_id=p["local"])
        if p.get("rota"):
            qs = qs.filter(urna__secao__rota__numero=p["rota"])
        agora = timezone.now()
        entregas = []
        for e in qs.order_by("urna__patrimonio"):
            sec = e.urna.secao
            local, rota = (sec.local if sec else None), (sec.rota if sec else None)
            entregas.append({
                **dados_urna(e.urna),
                "status": situacao(e, local, agora),
                "responsavel_distribuicao": e.responsavel_distribuicao or (rota.responsavel if rota else ""),
                "placa": rota.placa if rota else "",
                "presidente": local.presidente if local else "",
                "presidente_telefone": local.presidente_telefone if local else "",
                "data_entrega": local.data_entrega.isoformat() if local and local.data_entrega else None,
                "hora_saida": _hm(local.hora_saida) if local else None,
                "hora_prevista": _hm(local.hora_prevista) if local else None,
                "atraso_min": _atraso_min(e, local),
                "confirmado_em": e.confirmado_em,
                "ocorrencias": len(e.ocorrencias.all()),
            })
        resumo = {"total": len(entregas)}
        for k in ("entregue", "em_transito", AGUARDANDO, "pendencia"):
            resumo[k] = sum(1 for x in entregas if x["status"] == k)
        if p.get("status"):
            entregas = [x for x in entregas if x["status"] == p["status"]]
        return Response({
            "resumo": resumo,
            "rotas": list(Rota.objects.values_list("numero", flat=True)),
            "entregas": entregas,
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


class ImportarPresidentesView(APIView):
    """POST /api/importar-presidentes/ (multipart: arquivo) -- planilha só com os presidentes de prédio."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if arquivo is None:
            return erro("Envie o arquivo no campo 'arquivo'.")
        try:
            return Response(importar_presidentes(arquivo))
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
            "endereco": x.local.endereco, "bairro": x.local.bairro,
            "presidente": x.local.presidente, "presidente_telefone": x.local.presidente_telefone,
            "data_entrega": x.local.data_entrega.isoformat() if x.local.data_entrega else None,
            "hora_saida": _hm(x.local.hora_saida), "hora_prevista": _hm(x.local.hora_prevista),
            "municipio": x.local.municipio.nome, "municipio_id": x.local.municipio_id,
            "rota": x.rota.numero if x.rota else None,
            "rota_responsavel": x.rota.responsavel if x.rota else "",
            "rota_placa": x.rota.placa if x.rota else "",
            "rota_celular": x.rota.celular if x.rota else "",
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


# ---------- Edição pelo sistema (sem reimportar planilha) ----------

def _valor(dados, chave, conversor, rotulo):
    """Lê um campo opcional: vazio vira None; texto inválido levanta ValueError."""
    bruto = str(dados.get(chave) or "").strip()
    if not bruto:
        return None
    try:
        valor = conversor(bruto)
    except ValueError:
        valor = None
    if valor is None:
        raise ValueError(f"{rotulo} inválido(a): '{bruto}'.")
    return valor


def dados_local(local):
    return {
        "id": local.id,
        "presidente": local.presidente,
        "presidente_telefone": local.presidente_telefone,
        "data_entrega": local.data_entrega.isoformat() if local.data_entrega else None,
        "hora_saida": _hm(local.hora_saida),
        "hora_prevista": _hm(local.hora_prevista),
    }


class EditarLocalView(APIView):
    """PATCH /api/locais/<id>/ -- presidente, telefone, data de entrega e horários. Só muda o que for enviado."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        local = LocalVotacao.objects.filter(pk=pk).first()
        if local is None:
            return erro("Local não encontrado.", 404)
        d, campos = request.data, []
        for nome, limite in (("presidente", 120), ("presidente_telefone", 40)):
            if nome in d:
                setattr(local, nome, str(d[nome] or "").strip()[:limite])
                campos.append(nome)
        try:
            for chave, conversor, rotulo in (("data_entrega", parse_date, "Data de entrega"),
                                             ("hora_saida", parse_time, "Horário de saída"),
                                             ("hora_prevista", parse_time, "Horário previsto")):
                if chave in d:
                    setattr(local, chave, _valor(d, chave, conversor, rotulo))
                    campos.append(chave)
        except ValueError as e:
            return erro(str(e))
        if campos:
            local.save(update_fields=campos)
        return Response(dados_local(local))


class EditarRotaView(APIView):
    """PATCH /api/rotas/<numero>/ -- responsável pela distribuição, placa e celular."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, numero):
        rota = Rota.objects.filter(numero=numero).first()
        if rota is None:
            return erro("Rota não encontrada.", 404)
        campos = []
        for nome, limite in (("responsavel", 200), ("placa", 15), ("celular", 60)):
            if nome in request.data:
                setattr(rota, nome, str(request.data[nome] or "").strip()[:limite])
                campos.append(nome)
        if campos:
            rota.save(update_fields=campos)
        return Response({"numero": rota.numero, "responsavel": rota.responsavel,
                         "placa": rota.placa, "celular": rota.celular})


class ApagarDadosView(APIView):
    """
    GET  /api/apagar-dados/  -> o que cada opção apagaria hoje.
    POST /api/apagar-dados/  { escopo, confirmacao: "APAGAR" } -> faz uma cópia de segurança e apaga.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([
            {"id": k, "titulo": e["titulo"], "descricao": e["descricao"], "resumo": e["contar"]()}
            for k, e in ESCOPOS.items()
        ])

    def post(self, request):
        escopo = ESCOPOS.get(request.data.get("escopo"))
        if escopo is None:
            return erro("Escolha o que apagar.")
        if str(request.data.get("confirmacao", "")).strip().upper() != "APAGAR":
            return erro("Digite APAGAR para confirmar.")
        backup = copia_de_seguranca()
        with transaction.atomic():
            escopo["apagar"]()
        return Response({"detail": f"Dados apagados: {escopo['titulo']}.", "backup": backup})


class ImpactoRotaView(APIView):
    """GET /api/rotas/<n>/impacto/ -- o que seria apagado ao excluir a rota."""
    permission_classes = [IsAuthenticated]

    def get(self, request, numero):
        rota = Rota.objects.filter(numero=numero).first()
        return erro("Rota não encontrada.", 404) if rota is None else Response(impacto_rota(rota))


class ExcluirRotaView(APIView):
    """POST /api/rotas/<n>/excluir/ { modo: "so_rota" | "tudo", confirmacao: "APAGAR" }"""
    permission_classes = [IsAuthenticated]

    def post(self, request, numero):
        rota = Rota.objects.filter(numero=numero).first()
        if rota is None:
            return erro("Rota não encontrada.", 404)
        modo = request.data.get("modo")
        if modo not in ("so_rota", "tudo"):
            return erro("Escolha se quer excluir só a rota ou a rota e tudo dela.")
        if str(request.data.get("confirmacao", "")).strip().upper() != "APAGAR":
            return erro("Digite APAGAR para confirmar.")
        backup = copia_de_seguranca()
        excluir_rota(rota, modo)
        return Response({"detail": f"Rota {numero} excluída.", "backup": backup})


class ImpactoLocalView(APIView):
    """GET /api/locais/<id>/impacto/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        local = LocalVotacao.objects.filter(pk=pk).first()
        return erro("Local não encontrado.", 404) if local is None else Response(impacto_local(local))


class ExcluirLocalView(APIView):
    """POST /api/locais/<id>/excluir/ { confirmacao: "APAGAR" }"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        local = LocalVotacao.objects.filter(pk=pk).first()
        if local is None:
            return erro("Local não encontrado.", 404)
        if str(request.data.get("confirmacao", "")).strip().upper() != "APAGAR":
            return erro("Digite APAGAR para confirmar.")
        backup = copia_de_seguranca()
        nome = local.nome
        excluir_local(local)
        return Response({"detail": f"Local excluído: {nome}.", "backup": backup})
