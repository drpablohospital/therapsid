/**
 * SINAPSID - Módulo de Análisis de Tendencias Clínicas
 * Scripts para visualización con Plotly
 */

// Colores del tema DOGMA
const DOGMA_COLORS = {
    primary: '#4a90d9',
    primaryLight: '#6ba3e0',
    secondary: '#2c3e50',
    background: '#1a1a2e',
    grid: '#2d2d44',
    text: '#e0e0e0',
    textSecondary: '#888888',
    alert: '#e74c3c',
    warning: '#f39c12',
    success: '#27ae60',
    // Colores para diferentes series
    series: [
        '#4a90d9', '#e74c3c', '#27ae60', '#f39c12', 
        '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
    ]
};

// Rangos normales por variable
const VARIABLE_RANGES = {
    'Glasgow': { min: 3, max: 15, normalMin: 13, normalMax: 15, criticalLow: 8, criticalHigh: null },
    'RASS': { min: -5, max: 4, normalMin: -1, normalMax: 1, criticalLow: -4, criticalHigh: 3 },
    'CPOT': { min: 0, max: 8, normalMin: 0, normalMax: 2, criticalLow: null, criticalHigh: 4 },
    'FC': { min: 40, max: 180, normalMin: 60, normalMax: 100, criticalLow: 50, criticalHigh: 120 },
    'TAS': { min: 70, max: 220, normalMin: 90, normalMax: 140, criticalLow: 90, criticalHigh: 180 },
    'TAD': { min: 40, max: 140, normalMin: 60, normalMax: 90, criticalLow: 60, criticalHigh: null },
    'PAM': { min: 50, max: 140, normalMin: 70, normalMax: 105, criticalLow: 65, criticalHigh: null },
    'Lactato': { min: 0, max: 10, normalMin: 0.5, normalMax: 2, criticalLow: null, criticalHigh: 4 },
    'FR': { min: 8, max: 40, normalMin: 12, normalMax: 20, criticalLow: 8, criticalHigh: 30 },
    'SpO2': { min: 70, max: 100, normalMin: 95, normalMax: 100, criticalLow: 85, criticalHigh: null },
    'FiO2': { min: 21, max: 100, normalMin: 21, normalMax: 40, criticalLow: null, criticalHigh: 60 },
    'PaFi': { min: 50, max: 500, normalMin: 300, normalMax: 500, criticalLow: 200, criticalHigh: null },
    'PEEP': { min: 0, max: 20, normalMin: 5, normalMax: 8, criticalLow: null, criticalHigh: 12 },
    'Creatinina': { min: 0.3, max: 5, normalMin: 0.7, normalMax: 1.3, criticalLow: null, criticalHigh: 3 },
    'BUN': { min: 5, max: 100, normalMin: 7, normalMax: 20, criticalLow: null, criticalHigh: 30 },
    'Diuresis': { min: 0, max: 5000, normalMin: 800, normalMax: 2000, criticalLow: 400, criticalHigh: null },
    'Sodio': { min: 120, max: 160, normalMin: 135, normalMax: 145, criticalLow: 130, criticalHigh: 150 },
    'Potasio': { min: 2, max: 7, normalMin: 3.5, normalMax: 5, criticalLow: 3, criticalHigh: 5.5 },
    'Glucemia': { min: 40, max: 400, normalMin: 70, normalMax: 140, criticalLow: 70, criticalHigh: 180 },
    'Temperatura': { min: 34, max: 42, normalMin: 36.1, normalMax: 37.2, criticalLow: 35, criticalHigh: 38.5 },
    'Leucocitos': { min: 1000, max: 50000, normalMin: 4000, normalMax: 11000, criticalLow: 4000, criticalHigh: 12000 },
    'Hb': { min: 6, max: 18, normalMin: 12, normalMax: 16, criticalLow: 7, criticalHigh: null },
    'Plaquetas': { min: 20000, max: 500000, normalMin: 150000, normalMax: 400000, criticalLow: 50000, criticalHigh: null },
    'PCR': { min: 0, max: 500, normalMin: 0, normalMax: 5, criticalLow: null, criticalHigh: 100 },
    'INR': { min: 0.8, max: 5, normalMin: 0.9, normalMax: 1.1, criticalLow: null, criticalHigh: 1.5 },
};

// Unidades por variable
const VARIABLE_UNITS = {
    'Glasgow': '/15', 'RASS': '/4', 'CPOT': '/8',
    'FC': 'lpm', 'TAS': 'mmHg', 'TAD': 'mmHg', 'PAM': 'mmHg', 'Lactato': 'mmol/L',
    'FR': 'rpm', 'SpO2': '%', 'FiO2': '%', 'PaFi': '', 'PEEP': 'cmH2O',
    'Creatinina': 'mg/dL', 'BUN': 'mg/dL', 'Diuresis': 'mL/24h', 'Sodio': 'mEq/L', 'Potasio': 'mEq/L',
    'Glucemia': 'mg/dL', 'IMC': 'kg/m²', 'Temperatura': '°C',
    'Leucocitos': '×10³/μL', 'Hb': 'g/dL', 'Plaquetas': '×10³/μL', 'PCR': 'mg/L', 'INR': ''
};

// Variables por categoría
const VARIABLE_GROUPS = {
    neurologico: ['Glasgow', 'RASS', 'CPOT'],
    circulatorio: ['FC', 'TAS', 'TAD', 'PAM', 'Lactato'],
    ventilatorio: ['FR', 'SpO2', 'FiO2', 'PaFi', 'PEEP'],
    renal: ['Creatinina', 'BUN', 'Diuresis', 'Sodio', 'Potasio'],
    metabolico: ['Glucemia', 'IMC', 'Temperatura'],
    hematologico: ['Leucocitos', 'Hb', 'Plaquetas', 'PCR', 'INR']
};

// Configuración base de Plotly
function getBaseLayout(title) {
    return {
        title: {
            text: title,
            font: { color: DOGMA_COLORS.text, size: 16 },
            x: 0.5,
            xanchor: 'center'
        },
        paper_bgcolor: DOGMA_COLORS.background,
        plot_bgcolor: DOGMA_COLORS.background,
        font: { color: DOGMA_COLORS.text, family: 'Arial, sans-serif' },
        xaxis: {
            gridcolor: DOGMA_COLORS.grid,
            linecolor: DOGMA_COLORS.grid,
            tickfont: { color: DOGMA_COLORS.textSecondary },
            showgrid: true,
            zeroline: false
        },
        yaxis: {
            gridcolor: DOGMA_COLORS.grid,
            linecolor: DOGMA_COLORS.grid,
            tickfont: { color: DOGMA_COLORS.textSecondary },
            showgrid: true,
            zeroline: false
        },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            font: { color: DOGMA_COLORS.text },
            bgcolor: DOGMA_COLORS.secondary
        },
        margin: { l: 60, r: 40, t: 60, b: 40 }
    };
}

// Función para crear el gráfico de tendencias
function createTrendChart(containerId, data, selectedVars) {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) {
        if (container) {
            container.innerHTML = '<div class="alert alert-info">No hay datos disponibles para las variables seleccionadas.</div>';
        }
        return;
    }

    // Agrupar datos por variable
    const groupedData = {};
    data.forEach(point => {
        if (!groupedData[point.variable]) {
            groupedData[point.variable] = [];
        }
        groupedData[point.variable].push(point);
    });

    const traces = [];
    const shapes = [];
    const annotations = [];

    selectedVars.forEach((varName, index) => {
        const varData = groupedData[varName];
        if (!varData || varData.length === 0) return;

        const color = DOGMA_COLORS.series[index % DOGMA_COLORS.series.length];
        const range = VARIABLE_RANGES[varName];
        const unit = VARIABLE_UNITS[varName] || '';

        // Ordenar por fecha
        varData.sort((a, b) => new Date(a.fecha) - new Date(b.fecha));

        const dates = varData.map(d => d.fecha);
        const values = varData.map(d => d.valor);
        const sources = varData.map(d => d.fuente);

        // Marcar punto de ingreso
        const markerColors = sources.map(s => s === 'ingreso' ? '#ffffff' : color);
        const markerSizes = sources.map(s => s === 'ingreso' ? 12 : 8);
        const markerSymbols = sources.map(s => s === 'ingreso' ? 'diamond' : 'circle');

        // Trace principal
        traces.push({
            x: dates,
            y: values,
            mode: 'lines+markers',
            name: `${varName} ${unit}`,
            line: {
                color: color,
                width: 2,
                shape: 'spline'
            },
            marker: {
                color: markerColors,
                size: markerSizes,
                symbol: markerSymbols,
                line: { color: color, width: 2 }
            },
            hovertemplate: `<b>${varName}</b><br>Fecha: %{x}<br>Valor: %{y} ${unit}<br><extra></extra>`
        });

        // Agregar líneas de referencia si hay rangos
        if (range) {
            // Rango normal (fondo sombreado)
            if (range.normalMin !== null && range.normalMax !== null) {
                shapes.push({
                    type: 'rect',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.normalMin,
                    y1: range.normalMax,
                    fillcolor: 'rgba(39, 174, 96, 0.1)',
                    line: { width: 0 },
                    layer: 'below'
                });
            }

            // Umbrales críticos
            if (range.criticalLow !== null) {
                shapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.criticalLow,
                    y1: range.criticalLow,
                    line: {
                        color: 'rgba(231, 76, 60, 0.5)',
                        width: 1,
                        dash: 'dash'
                    }
                });
            }

            if (range.criticalHigh !== null) {
                shapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.criticalHigh,
                    y1: range.criticalHigh,
                    line: {
                        color: 'rgba(231, 76, 60, 0.5)',
                        width: 1,
                        dash: 'dash'
                    }
                });
            }

            // Umbrales específicos para PaFi (insuficiencia respiratoria)
            if (varName === 'PaFi') {
                [300, 200, 100].forEach((threshold, i) => {
                    const colors = ['rgba(243, 156, 18, 0.5)', 'rgba(230, 126, 34, 0.5)', 'rgba(231, 76, 60, 0.5)'];
                    const labels = ['Leve ARDS', 'Moderado ARDS', 'Severo ARDS'];
                    shapes.push({
                        type: 'line',
                        xref: 'x',
                        yref: 'y',
                        x0: dates[0],
                        x1: dates[dates.length - 1],
                        y0: threshold,
                        y1: threshold,
                        line: { color: colors[i], width: 1, dash: 'dot' }
                    });
                    annotations.push({
                        x: dates[dates.length - 1],
                        y: threshold,
                        xref: 'x',
                        yref: 'y',
                        text: labels[i],
                        showarrow: false,
                        font: { color: colors[i], size: 10 },
                        xanchor: 'left',
                        yanchor: 'bottom'
                    });
                });
            }
        }
    });

    const layout = getBaseLayout('Tendencias Clínicas');
    layout.shapes = shapes;
    layout.annotations = annotations;
    layout.yaxis.title = 'Valor';
    layout.xaxis.title = 'Fecha';

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToAdd: ['lasso2d', 'select2d'],
        modeBarButtonsToRemove: ['sendDataToCloud'],
        toImageButtonOptions: {
            format: 'png',
            filename: 'tendencias_clinicas',
            height: 600,
            width: 1000,
            scale: 2
        }
    };

    Plotly.newPlot(containerId, traces, layout, config);
}

// Función para crear gráficos individuales por variable
function createIndividualCharts(containerId, data, selectedVars) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Limpiar contenedor
    container.innerHTML = '';

    if (!data || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No hay datos disponibles.</div>';
        return;
    }

    // Agrupar datos por variable
    const groupedData = {};
    data.forEach(point => {
        if (!groupedData[point.variable]) {
            groupedData[point.variable] = [];
        }
        groupedData[point.variable].push(point);
    });

    selectedVars.forEach((varName, index) => {
        const varData = groupedData[varName];
        if (!varData || varData.length === 0) return;

        // Crear contenedor para este gráfico
        const chartContainer = document.createElement('div');
        chartContainer.className = 'mb-4';
        chartContainer.innerHTML = `
            <div class="card bg-dark">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0 text-light">${varName} ${VARIABLE_UNITS[varName] || ''}</h6>
                    <span class="badge bg-secondary" id="stats-${varName}"></span>
                </div>
                <div class="card-body p-0">
                    <div id="chart-${varName}" style="height: 250px;"></div>
                </div>
            </div>
        `;
        container.appendChild(chartContainer);

        // Ordenar por fecha
        varData.sort((a, b) => new Date(a.fecha) - new Date(b.fecha));

        const dates = varData.map(d => d.fecha);
        const values = varData.map(d => d.valor);
        const sources = varData.map(d => d.fuente);

        const color = DOGMA_COLORS.series[index % DOGMA_COLORS.series.length];
        const range = VARIABLE_RANGES[varName];

        // Marcar punto de ingreso
        const markerColors = sources.map(s => s === 'ingreso' ? '#ffffff' : color);
        const markerSizes = sources.map(s => s === 'ingreso' ? 14 : 8);
        const markerSymbols = sources.map(s => s === 'ingreso' ? 'diamond' : 'circle');

        const traces = [{
            x: dates,
            y: values,
            mode: 'lines+markers',
            type: 'scatter',
            name: varName,
            line: { color: color, width: 2, shape: 'spline' },
            marker: {
                color: markerColors,
                size: markerSizes,
                symbol: markerSymbols,
                line: { color: color, width: 2 }
            },
            fill: 'tozeroy',
            fillcolor: color + '20'
        }];

        const shapes = [];
        const annotations = [];

        if (range) {
            // Rango normal
            if (range.normalMin !== null && range.normalMax !== null) {
                shapes.push({
                    type: 'rect',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.normalMin,
                    y1: range.normalMax,
                    fillcolor: 'rgba(39, 174, 96, 0.15)',
                    line: { width: 0 },
                    layer: 'below'
                });
            }

            // Líneas de umbral
            if (range.criticalLow !== null) {
                shapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.criticalLow,
                    y1: range.criticalLow,
                    line: { color: 'rgba(231, 76, 60, 0.7)', width: 1, dash: 'dash' }
                });
            }
            if (range.criticalHigh !== null) {
                shapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'y',
                    x0: dates[0],
                    x1: dates[dates.length - 1],
                    y0: range.criticalHigh,
                    y1: range.criticalHigh,
                    line: { color: 'rgba(231, 76, 60, 0.7)', width: 1, dash: 'dash' }
                });
            }

            // Rango del eje Y
            const yRange = [range.min || Math.min(...values) * 0.9, range.max || Math.max(...values) * 1.1];
        }

        const layout = {
            paper_bgcolor: DOGMA_COLORS.background,
            plot_bgcolor: DOGMA_COLORS.background,
            font: { color: DOGMA_COLORS.text, family: 'Arial, sans-serif', size: 11 },
            margin: { l: 50, r: 20, t: 20, b: 40 },
            xaxis: {
                gridcolor: DOGMA_COLORS.grid,
                linecolor: DOGMA_COLORS.grid,
                tickfont: { color: DOGMA_COLORS.textSecondary, size: 10 },
                showgrid: true
            },
            yaxis: {
                gridcolor: DOGMA_COLORS.grid,
                linecolor: DOGMA_COLORS.grid,
                tickfont: { color: DOGMA_COLORS.textSecondary, size: 10 },
                showgrid: true,
                range: range ? [range.min, range.max] : undefined
            },
            shapes: shapes,
            annotations: annotations,
            showlegend: false,
            hovermode: 'x unified'
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(`chart-${varName}`, traces, layout, config);

        // Calcular y mostrar estadísticas
        const stats = calculateStats(values);
        const statsBadge = document.getElementById(`stats-${varName}`);
        if (statsBadge && stats) {
            statsBadge.innerHTML = `Último: <strong>${stats.last}</strong> | Media: ${stats.mean} | Min: ${stats.min} | Max: ${stats.max}`;
        }
    });
}

// Calcular estadísticas básicas
function calculateStats(values) {
    const validValues = values.filter(v => v !== null && v !== undefined && !isNaN(v));
    if (validValues.length === 0) return null;

    const sum = validValues.reduce((a, b) => a + b, 0);
    const avg = sum / validValues.length;
    const min = Math.min(...validValues);
    const max = Math.max(...validValues);

    return {
        count: validValues.length,
        mean: avg.toFixed(2),
        min: min.toFixed(2),
        max: max.toFixed(2),
        last: validValues[validValues.length - 1].toFixed(2)
    };
}

// Función para actualizar la tabla de datos
function updateDataTable(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!data || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No hay datos para mostrar.</div>';
        return;
    }

    // Agrupar por fecha
    const groupedByDate = {};
    data.forEach(point => {
        if (!groupedByDate[point.fecha]) {
            groupedByDate[point.fecha] = {};
        }
        groupedByDate[point.fecha][point.variable] = {
            valor: point.valor,
            fuente: point.fuente
        };
    });

    // Obtener todas las variables únicas
    const allVars = [...new Set(data.map(d => d.variable))].sort();

    // Crear tabla
    let html = `
        <div class="table-responsive">
            <table class="table table-dark table-sm table-hover">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Fuente</th>
                        ${allVars.map(v => `<th>${v} ${VARIABLE_UNITS[v] || ''}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;

    Object.keys(groupedByDate).sort().forEach(date => {
        const dateData = groupedByDate[date];
        const fuente = dateData[Object.keys(dateData)[0]]?.fuente || '-';
        const fuenteBadge = fuente === 'ingreso' 
            ? '<span class="badge bg-primary">Ingreso</span>'
            : '<span class="badge bg-secondary">Evolución</span>';

        html += '<tr>';
        html += `<td class="fw-bold">${date}</td>`;
        html += `<td>${fuenteBadge}</td>`;
        
        allVars.forEach(varName => {
            const varData = dateData[varName];
            if (varData) {
                const range = VARIABLE_RANGES[varName];
                let valueClass = '';
                
                if (range) {
                    if (range.criticalHigh && varData.valor > range.criticalHigh) {
                        valueClass = 'text-danger fw-bold';
                    } else if (range.criticalLow && varData.valor < range.criticalLow) {
                        valueClass = 'text-danger fw-bold';
                    } else if (varData.valor < range.normalMin || varData.valor > range.normalMax) {
                        valueClass = 'text-warning';
                    } else {
                        valueClass = 'text-success';
                    }
                }
                
                html += `<td class="${valueClass}">${varData.valor}</td>`;
            } else {
                html += '<td class="text-muted">-</td>';
            }
        });
        
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Función para exportar datos a CSV
function exportToCSV(data, filename = 'tendencias_clinicas.csv') {
    if (!data || data.length === 0) {
        alert('No hay datos para exportar');
        return;
    }

    // Obtener todas las columnas
    const columns = ['fecha', 'variable', 'valor', 'fuente'];
    
    // Crear CSV
    let csv = columns.join(',') + '\n';
    
    data.forEach(row => {
        const values = columns.map(col => {
            const val = row[col];
            // Escapar si contiene comas
            if (typeof val === 'string' && val.includes(',')) {
                return `"${val}"`;
            }
            return val;
        });
        csv += values.join(',') + '\n';
    });

    // Descargar
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
}

// Función para cargar datos desde la API
async function loadTrendsData(patientId, variables, startDate, endDate) {
    try {
        const params = new URLSearchParams();
        if (variables && variables.length > 0) {
            params.append('variables', variables.join(','));
        }
        if (startDate) params.append('start', startDate);
        if (endDate) params.append('end', endDate);

        const response = await fetch(`/api/trends/${patientId}?${params.toString()}`);
        if (!response.ok) {
            throw new Error('Error cargando datos');
        }
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return [];
    }
}

// Función para buscar pacientes
async function searchPatients(query) {
    try {
        const response = await fetch(`/api/patients/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Error buscando pacientes');
        }
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return [];
    }
}

// Inicializar datepickers
function initDatepickers() {
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);

    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (startDateInput) {
        startDateInput.value = oneMonthAgo.toISOString().split('T')[0];
    }
    if (endDateInput) {
        endDateInput.value = today.toISOString().split('T')[0];
    }
}

// Inicializar todo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initDatepickers();
    
    // Botón de actualizar
    const btnActualizar = document.getElementById('btn-actualizar');
    if (btnActualizar) {
        btnActualizar.addEventListener('click', function() {
            const patientId = document.getElementById('patient-select')?.value;
            if (!patientId) {
                alert('Por favor seleccione un paciente');
                return;
            }

            const startDate = document.getElementById('start-date')?.value;
            const endDate = document.getElementById('end-date')?.value;

            // Obtener variables seleccionadas según el tab activo
            const activeTab = document.querySelector('.tab-pane.active');
            const checkboxes = activeTab?.querySelectorAll('input[type="checkbox"]:checked');
            const variables = Array.from(checkboxes || []).map(cb => cb.value);

            if (variables.length === 0) {
                alert('Por favor seleccione al menos una variable');
                return;
            }

            // Cargar y mostrar datos
            loadTrendsData(patientId, variables, startDate, endDate).then(data => {
                const containerId = activeTab?.querySelector('[id^="chart-"]')?.id || 'trend-chart';
                createIndividualCharts(containerId, data, variables);
                updateDataTable('data-table', data);
            });
        });
    }

    // Botón de exportar
    const btnExportar = document.getElementById('btn-exportar');
    if (btnExportar) {
        btnExportar.addEventListener('click', function() {
            const patientId = document.getElementById('patient-select')?.value;
            if (!patientId) {
                alert('Por favor seleccione un paciente');
                return;
            }

            const startDate = document.getElementById('start-date')?.value;
            const endDate = document.getElementById('end-date')?.value;

            loadTrendsData(patientId, null, startDate, endDate).then(data => {
                exportToCSV(data, `tendencias_paciente_${patientId}.csv`);
            });
        });
    }
});

// Exportar funciones para uso global
window.ClinicalAnalysis = {
    createTrendChart,
    createIndividualCharts,
    updateDataTable,
    exportToCSV,
    loadTrendsData,
    searchPatients,
    VARIABLE_GROUPS,
    VARIABLE_RANGES,
    VARIABLE_UNITS,
    DOGMA_COLORS
};
