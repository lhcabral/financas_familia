from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class LoginObrigatorioMiddleware:
    """Redireciona visitantes sem sessão para a tela de entrada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated or self._liberado(request.path_info):
            return self.get_response(request)
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

    def _liberado(self, path):
        return path.startswith((settings.LOGIN_URL, '/admin/', '/static/'))
