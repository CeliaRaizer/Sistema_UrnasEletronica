from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginAPIView(APIView):
    """
    POST /api/login/
    Recebe { "username": "...", "password": "..." }
    Retorna um token de autenticacao se as credenciais forem validas.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Informe usuario e senha."},
                status=400,
            )

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {"detail": "Usuario ou senha invalidos."},
                status=401,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "username": user.username,
        })


class LogoutAPIView(APIView):
    """POST /api/logout/ -- invalida o token atual do usuario."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({"detail": "Sessao encerrada."})


class MeAPIView(APIView):
    """
    GET /api/me/
    Endpoint protegido de exemplo -- so responde se o token
    enviado no header Authorization for valido.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "email": request.user.email,
        })
