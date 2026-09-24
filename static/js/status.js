(() => {
    const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';
    const cartoes = JSON.parse(document.getElementById('cartoes-data')?.textContent || '[]');
    const modal = document.getElementById('modal-cartao');
    const listaCartoes = document.getElementById('lista-cartoes');

    function formatarBrl(valor) {
        const numero = Number(valor || 0);
        return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function aplicarClasseStatus(select, status) {
        select.classList.remove('status-aberto', 'status-fechado', 'status-cartao');
        select.classList.add(`status-${status}`);
        select.dataset.statusAtual = status;
        select.dataset.aberto = (status === 'aberto' || status === 'previsto') ? '1' : '0';
    }

    function ehPendente(status) {
        return status === 'aberto' || status === 'previsto';
    }

    function ajustarAPagar(select, statusNovo) {
        const alvo = document.querySelector('[data-a-pagar], [data-a-receber]');
        if (!alvo) return;
        const valor = Number(String(select.dataset.valor || '0').replace(',', '.'));
        const eraAberto = ehPendente(select.dataset.statusAtual);
        const seraAberto = ehPendente(statusNovo);
        let atual = Number(alvo.dataset.aPagarValor || alvo.dataset.aPagarvalor || '0');
        if (Number.isNaN(atual)) atual = 0;
        if (eraAberto && !seraAberto) atual -= valor;
        if (!eraAberto && seraAberto) atual += valor;
        if (atual < 0.005 && atual > -0.005) atual = 0;
        alvo.dataset.aPagarValor = String(atual);
        alvo.textContent = formatarBrl(atual);
    }

    function atualizarVinculo(select, dados) {
        const linha = select.closest('tr');
        const alvo = linha?.querySelector('[data-vinculo-cartao]');
        if (!alvo) return;
        if (dados.fatura_url && dados.cartao_nome) {
            alvo.outerHTML = `<a class="vinculo-cartao" href="${dados.fatura_url}" data-vinculo-cartao>${dados.cartao_nome}</a>`;
        } else {
            alvo.innerHTML = '';
            alvo.removeAttribute('href');
        }
    }

    function escolherCartao() {
        return new Promise((resolve) => {
            if (!cartoes.length) {
                window.alert('Cadastre um cartão antes de lançar a conta na fatura.');
                resolve(null);
                return;
            }
            if (cartoes.length === 1) {
                resolve(String(cartoes[0].id));
                return;
            }
            if (!modal || !listaCartoes) {
                resolve(String(cartoes[0].id));
                return;
            }
            listaCartoes.innerHTML = cartoes.map((cartao, indice) => `
                <label class="opcao-cartao">
                    <input type="radio" name="cartao-escolhido" value="${cartao.id}" ${indice === 0 ? 'checked' : ''}>
                    <span>${cartao.nome}</span>
                </label>
            `).join('');

            const finalizar = (evento) => {
                modal.removeEventListener('close', finalizar);
                if (modal.returnValue === 'ok') {
                    const marcado = modal.querySelector('input[name="cartao-escolhido"]:checked');
                    resolve(marcado ? marcado.value : null);
                } else {
                    resolve(null);
                }
            };
            modal.addEventListener('close', finalizar);
            if (typeof modal.showModal === 'function') {
                modal.showModal();
            } else {
                resolve(String(cartoes[0].id));
            }
        });
    }

    async function salvarStatus(select, status, cartaoId) {
        const corpo = new URLSearchParams({ status });
        if (cartaoId) corpo.set('cartao_id', cartaoId);
        const resposta = await fetch(select.dataset.url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrf(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: corpo,
        });
        const dados = await resposta.json();
        if (!resposta.ok || !dados.ok) {
            throw new Error(dados.erro || 'Não foi possível atualizar o status.');
        }
        return dados;
    }

    document.addEventListener('change', async (evento) => {
        const select = evento.target.closest('.seletor-status');
        if (!select) return;

        const anterior = select.dataset.statusAtual;
        const status = select.value;
        select.disabled = true;

        try {
            let cartaoId = null;
            if (status === 'cartao' && select.dataset.permiteCartao === '1') {
                cartaoId = await escolherCartao();
                if (!cartaoId) {
                    select.value = anterior;
                    return;
                }
            }
            const dados = await salvarStatus(select, status, cartaoId);
            ajustarAPagar(select, dados.status);
            aplicarClasseStatus(select, dados.status);
            atualizarVinculo(select, dados);
        } catch (erro) {
            select.value = anterior;
            window.alert(erro.message);
        } finally {
            select.disabled = false;
        }
    });
})();
