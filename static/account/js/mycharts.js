document.addEventListener('DOMContentLoaded', function () {

    // dashbaord domut chart
    const ctx = document.getElementById('donutChart');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Remaining'],
            datasets: [{
                data: [70, 30],
                backgroundColor: ['#187c59', '#ffffff'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            cutout: '85%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true
                }
            }
        }
    });

    // The performance yield 

    function createFadeGradient(ctx, chartArea, color) {
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, color.replace('1)', '0.35)'));
        gradient.addColorStop(1, color.replace('1)', '0)'));
        return gradient;
    }

    const ctx2 = document.getElementById('lineChart');

    new Chart(ctx2, {
        type: 'line',
        data: {
            labels: ['01', '02', '03', '04', '05', '06'],
            datasets: [
                {
                    label: 'Current Year',
                    data: [3000, 4500, 5000, 6000, 5550, 6500],
                    borderColor: 'rgba(3, 112, 99, 1)',
                    borderWidth: 4,
                    borderCapStyle: 'round',
                    borderJoinStyle: 'round',
                    tension: 0.45,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: (context) => {
                        const { chart } = context;
                        if (!chart.chartArea) return null;

                        return createFadeGradient(
                            chart.ctx,
                            chart.chartArea,
                            'rgba(3, 112, 99, 1)'
                        );
                    }
                },
                {
                    label: 'Previous Year',
                    data: [200, 350, 7000, 500, 4502, 600],
                    borderColor: 'rgba(13, 110, 253, 0.4)',
                    borderWidth: 2,
                    borderCapStyle: 'round',
                    borderJoinStyle: 'round',
                    tension: 0.45,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: (context) => {
                        const { chart } = context;
                        if (!chart.chartArea) return null;

                        return createFadeGradient(
                            chart.ctx,
                            chart.chartArea,
                            'rgba(13, 110, 253, 1)'
                        );
                    }
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f1f1f1' },
                    ticks: { display: false }
                }
            }
        }
    });



    // double chart
    function createGradient(ctx3, chartArea, color) {
        const gradient = ctx3.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, color.replace('1)', '0.35)'));
        gradient.addColorStop(1, color.replace('1)', '0)'));
        return gradient;
    }

    function buildChart(canvasId, dataPoints, lineColor) {
        const canvas = document.getElementById(canvasId);
        const ctx3 = canvas.getContext('2d');

        return new Chart(ctx3, {
            type: 'line',
            data: {
                labels: dataPoints.map((_, i) => i),
                datasets: [{
                    data: dataPoints,
                    borderColor: lineColor,
                    borderCapStyle: 'round',
                    borderJoinStyle: 'round',
                    borderWidth: 3,
                    tension: 0.45,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: (context) => {
                        const { chart } = context;
                        if (!chart.chartArea) return null;

                        return createGradient(
                            chart.ctx,        // ✅ Chart.js internal context
                            chart.chartArea,
                            lineColor
                        );
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    }


    // UPWARD TREND (Green)
    buildChart(
        'upChart',
        [20, 25, 28, 35, 40, 38, 37],
        'rgba(25, 135, 84, 1)'
    );

    // DOWNWARD TREND (Red)
    buildChart(
        'downChart',
        [60, 55, 70, 48, 92, 98, 50],
        'rgba(220, 53, 69, 1)'
    );
});