from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.contrib.auth.views import LoginView, LogoutView


class FormularioEntrada(AuthenticationForm):
    username = UsernameField(
        label='Usuário',
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        }),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    error_messages = {
        'invalid_login': 'Usuário ou senha incorretos.',
        'inactive': 'Esta conta está inativa.',
    }


class EntrarView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = FormularioEntrada
    redirect_authenticated_user = True


class SairView(LogoutView):
    http_method_names = ['post', 'options']
