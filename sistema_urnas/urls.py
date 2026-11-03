from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path


def site_react(request, caminho=""):
    """Qualquer endereço que não seja /api/ ou /admin/ abre o site React (ex.: /confirmar)."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        raise Http404("Site não compilado. Rode 'npm run build' na pasta frontend.")
    return FileResponse(open(index, "rb"), content_type="text/html")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    re_path(r'^(?!api/|admin/|static/)(?P<caminho>.*)$', site_react),
]
