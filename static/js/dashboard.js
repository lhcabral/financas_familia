(() => {
    const fonte = document.getElementById('dados-grafico');
    if (!fonte || typeof window.Chart === 'undefined') return;

    const dados = JSON.parse(fonte.textContent || '{}');
    const texto = '#1d2a24';
    const grade = '#e0d6c6';

    const mensal = document.getElementById('grafico-mensal');
    if (mensal) {
        new window.Chart(mensal, {
            type: 'bar',
            data: {
                labels: dados.labels || [],
                datasets: [
                    {
                        label: 'Receitas',
                        data: dados.receitas || [],
                        backgroundColor: '#2f6a50',
                        borderRadius: 8,
                    },
                    {
                        label: 'Despesas',
                        data: dados.despesas || [],
                        backgroundColor: '#b85a38',
                        borderRadius: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: texto, boxWidth: 12 } } },
                scales: {
                    x: { ticks: { color: texto }, grid: { color: grade } },
                    y: { ticks: { color: texto }, grid: { color: grade } },
                },
            },
        });
    }

    const composicao = document.getElementById('grafico-composicao');
    if (composicao) {
        new window.Chart(composicao, {
            type: 'doughnut',
            data: {
                labels: dados.composicao_labels || [],
                datasets: [{
                    data: dados.composicao_valores || [],
                    backgroundColor: ['#1f4d3a', '#c9a15b', '#c9782b', '#b85a38'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '62%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: texto, boxWidth: 12, padding: 10 },
                    },
                },
            },
        });
    }
})();
