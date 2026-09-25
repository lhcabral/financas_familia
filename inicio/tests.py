from django.contrib.auth.models import User
from django.test import TestCase


class AcessoTests(TestCase):
    def test_visitante_e_enviado_para_o_login(self):
        resposta = self.client.get('/')
        self.assertRedirects(resposta, '/entrar/?next=/')

    def test_login_correto_abre_o_inicio(self):
        User.objects.create_user('familia', password='senha-teste-123')
        self.client.login(username='familia', password='senha-teste-123')
        resposta = self.client.get('/')
        self.assertEqual(resposta.status_code, 200)

    def test_senha_errada_permanece_na_tela(self):
        User.objects.create_user('familia', password='senha-teste-123')
        resposta = self.client.post('/entrar/', {
            'username': 'familia',
            'password': 'errada',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Usuário ou senha incorretos.')

    def test_sair_encerra_a_sessao(self):
        User.objects.create_user('familia', password='senha-teste-123')
        self.client.login(username='familia', password='senha-teste-123')
        resposta = self.client.post('/sair/')
        self.assertRedirects(resposta, '/entrar/')
        bloqueado = self.client.get('/')
        self.assertRedirects(bloqueado, '/entrar/?next=/')
