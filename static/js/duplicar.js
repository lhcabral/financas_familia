(() => {
    const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';
    const modal = document.getElementById('modal-duplicar');
    const form = document.getElementById('form-duplicar');
    const campos = document.getElementById('campos-duplicar');
    const titulo = document.getElementById('titulo-duplicar');
    const erro = document.getElementById('erro-duplicar');
    const cancelar = document.getElementById('cancelar-duplicar');

    if (!modal || !form || !campos) return;

    function mostrarErro(mensagem) {
        if (!erro) return;
        if (mensagem) {
            erro.hidden = false;
            erro.textContent = mensagem;
        } else {
            erro.hidden = true;
            erro.textContent = '';
        }
    }

    async function abrir(url) {
        mostrarErro('');
        const resposta = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const dados = await resposta.json();
        if (!resposta.ok || !dados.ok) {
            throw new Error(dados.erro || 'Não foi possível carregar os dados para duplicar.');
        }
        if (titulo) titulo.textContent = dados.titulo || 'Duplicar';
        campos.innerHTML = dados.html;
        form.dataset.url = url;
        if (typeof modal.showModal === 'function') {
            modal.showModal();
        }
    }

    document.addEventListener('click', async (evento) => {
        const botao = evento.target.closest('[data-duplicar]');
        if (!botao) return;
        evento.preventDefault();
        botao.disabled = true;
        try {
            await abrir(botao.dataset.duplicar);
        } catch (exc) {
            window.alert(exc.message);
        } finally {
            botao.disabled = false;
        }
    });

    cancelar?.addEventListener('click', () => modal.close());

    form.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        const url = form.dataset.url;
        if (!url) return;
        const corpo = new FormData(form);
        corpo.set('csrfmiddlewaretoken', csrf());
        const botao = form.querySelector('button[type="submit"]');
        if (botao) botao.disabled = true;
        try {
            const resposta = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: corpo,
            });
            const dados = await resposta.json();
            if (resposta.ok && dados.ok) {
                window.location.reload();
                return;
            }
            if (dados.html) campos.innerHTML = dados.html;
            mostrarErro(dados.erro || 'Confira os campos e tente de novo.');
        } catch (exc) {
            mostrarErro(exc.message);
        } finally {
            if (botao) botao.disabled = false;
        }
    });
})();
