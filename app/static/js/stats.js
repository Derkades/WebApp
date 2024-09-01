const commonOptions = {
    backgroundColor: 'transparent',
    textStyle: {
        fontFamily: 'Quicksand',
    },
    color: [
        '#dd6b66',
        '#759aa0',
        '#e69d87',
        '#8dc1a9',
        '#ea7e53',
        '#eedd78',
        '#73a373',
        '#73b9bc',
        '#7289ab',
        '#91ca8c',
        '#f49f42',
        '#a77fdd',
        '#dd7f98',
        '#ddab7f',
        '#7f91dd',
    ],
};

const chartsContainer = document.getElementById('charts');
const spinner = document.getElementById('spinner');
const buttons = {
    day: document.getElementById('day'),
    week: document.getElementById('week'),
    month: document.getElementById('month'),
    year: document.getElementById('year'),
    all: document.getElementById('all'),
};
const charts = [];

async function loadCharts(button) {
    // Immediately change buttons and remove old charts for responsiveness
    for (const otherButton of Object.values(buttons)) {
        otherButton.disabled = false;
    }
    button.disabled = true;

    chartsContainer.replaceChildren();

    // Download data
    spinner.classList.remove('hidden');
    const response = await fetch('/stats/data?period=' + encodeURIComponent(button.id));
    const data = await response.json();
    spinner.classList.add('hidden');

    charts.length = 0; // Clear old charts

    // Render charts
    for (const options of data) {
        const chartElem = document.createElement('div');
        chartElem.style.width = '100%';
        chartElem.style.height = '30rem';
        chartElem.style.marginBottom = '1rem';
        chartsContainer.append(chartElem);

        const eChart = echarts.init(chartElem, 'dark');
        eChart.setOption({...options, ...commonOptions});
        charts.push(eChart);
    }
}

// Delayed resize, to avoid redrawing charts many times during a resize
let resizeTimerId = 0;

function doResize() {
    charts.forEach(chart => chart.resize());
}

function delayedResize() {
    if (resizeTimerId != 0) {
        clearTimeout(resizeTimerId);
        resizeTimerId = 0;
    }
    resizeTimerId = setTimeout(doResize, 100);
}

document.addEventListener('DOMContentLoaded', () => {
    let foundHash = false;
    for (const buttonName in buttons) {
        if (window.location.hash == '#' + buttonName) {
            console.info(buttonName);
            loadCharts(buttons[buttonName]);
            foundHash = true;
            break;
        }
    }

    if (!foundHash) {
        loadCharts(buttons['week'])
    }

    for (const buttonName in buttons) {
        const button = buttons[buttonName];
        button.addEventListener('click', () => {
            window.location.hash = buttonName;
            loadCharts(button);
        });
    }

    window.addEventListener('resize', delayedResize);
});
