// https://github.com/nhn/tui.chart/blob/main/docs/en/common-theme.md
const theme = {
    chart: {
        backgroundColor: 'transparent',
    },
    title: {
        color: 'white',
        fontFamily: 'Quicksand',
    },
    xAxis: {
        title: {
            color: 'white',
            fontFamily: 'Quicksand',
        },
        label: {
            color: 'white',
            fontFamily: 'Quicksand',
        },
        color: 'white',
    },
    yAxis: {
        title: {
            color: 'white',
            fontFamily: 'Quicksand',
        },
        label: {
            color: 'white',
            fontFamily: 'Quicksand',
        },
        color: 'white',
    },
    legend: {
        label: {
            color: 'white',
            fontFamily: 'Quicksand',
        }
    },
    tooltip: {
        header: {
            fontFamily: 'Quicksand',
        },
        body: {
            fontFamily: 'Quicksand',
        },
    },
    plot: {
        vertical: {
            lineColor: 'transparent',
        },
        horizontal: {
            lineColor: 'transparent',
        }
    },
}

const chartsContainer = document.getElementById('charts');
const spinner = document.getElementById('spinner');
const buttons = {
    day: document.getElementById('day'),
    week: document.getElementById('week'),
    month: document.getElementById('month'),
    year: document.getElementById('year'),
};

async function loadCharts(button) {
    // Immediately change buttons and remove old charts for responsiveness
    for (const otherButton of Object.values(buttons)) {
        otherButton.disabled = false;
    }
    button.disabled = true;

    chartsContainer.replaceChildren();
    spinner.classList.remove('hidden');

    // Download data
    const response = await fetch('/stats/data?period=' + encodeURIComponent(button.id));
    const data = await response.json();

    spinner.classList.add('hidden');

    // Render charts
    for (const chart of data) {
        const chartElem = document.createElement('div');
        chartElem.style.width = '100%';
        chartElem.style.height = '30rem';
        chartElem.style.marginBottom = '1rem';
        chartsContainer.append(chartElem);
        // const args = {el: chartElem, data: chart['data'], options: chart['options']};

        // args.options.theme = theme;
        // Disable Google tracking: https://github.com/nhn/tui.chart/tree/main/apps/chart#collect-statistics-on-the-use-of-open-source
        // This was caught by our strict Content-Security-Policy :)
        // args.options.usageStatistics = false;
        const eChart = echarts.init(chartElem);
        eChart.setOption({

        });
        // switch (chart['type']) {
        //     case 'bar':
        //         toastui.Chart.barChart(args);
        //         break;
        //     case 'column':
        //         toastui.Chart.columnChart(args);
        //         break;
        //     case 'line':
        //         toastui.Chart.lineChart(args);
        //         break;
        //     default:
        //         throw new Error('invalid type: ' + chart['type']);
        //         break;
        // }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    for (const buttonName in buttons) {
        const button = buttons[buttonName];
        button.addEventListener('click', () => {
            window.location.hash = buttonName;
            loadCharts(button);
        });
    }

    let foundHash = false;
    for (const buttonName in buttons) {
        if (window.location.hash == '#' + buttonName) {
            loadCharts(buttons[buttonName]);
            foundHash = true;
            break;
        }
    }

    if (!foundHash) {
        loadCharts('week', buttons['week'])
    }
});
