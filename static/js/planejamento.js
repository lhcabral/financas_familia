(() => {
    const fonte = document.getElementById('dados-planejamento');
    const canvas = document.getElementById('grafico-parcelas');
    if (!fonte || !canvas || typeof window.Chart === 'undefined') return;

    const dados = JSON.parse(fonte.textContent || '{}');
    const texto = '#1d2a24';
    const grade = '#e0d6c6';
    const conjuntos = [{
        type: 'bar',
        label: 'Parcelas',
        data: dados.parcelas || [],
        backgroundColor: '#c9782b',
        borderRadius: 8,
    }];
    if ((dados.limite || []).length) {
        conjuntos.push({
            type: 'line',
            label: '30% da renda',
            data: dados.limite,
            borderColor: '#b85a38',
            borderDash: [6, 4],
            borderWidth: 2,
            pointRadius: 0,
        });
    }

    new window.Chart(canvas, {
        data: { labels: dados.labels || [], datasets: conjuntos },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: texto, boxWidth: 12 } } },
            scales: {
                x: { ticks: { color: texto }, grid: { color: grade } },
                y: { ticks: { color: texto }, grid: { color: grade }, beginAtZero: true },
            },
        },
    });
})();
