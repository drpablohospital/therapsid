/**
 * SINAPSID FLASK - JavaScript Helper
 * Maneja tablas dinámicas, guardado automático y cálculos en tiempo real
 */

// Guardado automático al cambiar pestañas
let currentPatientId = null;
let autoSaveInterval = null;

function initAutoSave(patientId) {
    currentPatientId = patientId;
    
    // Guardar cada 30 segundos
    autoSaveInterval = setInterval(() => {
        saveCurrentTab();
    }, 30000);
    
    // Guardar al cambiar de pestaña
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            saveCurrentTab();
        });
    });
    
    // Guardar al modificar campos (debounce de 2 segundos)
    let timeout;
    document.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('change', () => {
            clearTimeout(timeout);
            timeout = setTimeout(saveCurrentTab, 2000);
        });
    });
}

function saveCurrentTab() {
    if (!currentPatientId) return;
    
    const form = document.getElementById('patientForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    fetch(`/api/patient/${currentPatientId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            showToast('✓ Guardado automático', 'success');
        }
    })
    .catch(() => {});
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#4ade80' : type === 'error' ? '#ff6b6b' : '#ff6b35'};
        color: ${type === 'success' ? '#000' : '#fff'};
        border-radius: 4px;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Tablas Dinámicas
const DYNAMIC_TABLES = {
    'neurologicos': ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'hemodinamicos': ['medicamento', 'unidad', 'dosis_max', 'dosis_min', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'nefro': ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
    'gastro': ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
    'hematologica': ['medicamento', 'dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'cultivos': ['tipo', 'fecha', 'resultado', 'sensibilidad', 'resistencia'],
    'transfusiones': ['componente', 'dosis_unidades', 'dosis_ml', 'fecha_transfusion', 'reaccion_adversa']
};

function addTableRow(tableId, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const columns = DYNAMIC_TABLES[tableId];
    if (!columns) return;
    
    const row = document.createElement('tr');
    row.dataset.tempId = Date.now();
    
    columns.forEach(col => {
        const td = document.createElement('td');
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `${tableId}[${row.dataset.tempId}][${col}]`;
        input.className = 'table-input';
        input.style.cssText = 'width: 100%; background: transparent; border: 1px solid #444; color: #e0e0e0; padding: 5px;';
        
        if (col.includes('fecha')) {
            input.type = 'date';
            input.value = new Date().toISOString().split('T')[0];
        }
        
        td.appendChild(input);
        row.appendChild(td);
    });
    
    // Botón eliminar
    const tdDelete = document.createElement('td');
    tdDelete.innerHTML = '<button type="button" onclick="this.closest(\'tr\').remove()" class="btn btn-danger" style="padding: 3px 8px; font-size: 0.75rem;">✕</button>';
    row.appendChild(tdDelete);
    
    container.appendChild(row);
}

function saveDynamicTable(tableId, patientId) {
    const rows = document.querySelectorAll(`#table-${tableId} tbody tr`);
    const columns = DYNAMIC_TABLES[tableId];
    
    const data = [];
    rows.forEach(row => {
        const rowData = {};
        columns.forEach(col => {
            const input = row.querySelector(`input[name*="[${col}]"]`);
            if (input) {
                rowData[col] = input.value;
            }
        });
        if (Object.keys(rowData).length > 0 && Object.values(rowData).some(v => v)) {
            data.push(rowData);
        }
    });
    
    // Guardar cada fila
    data.forEach(item => {
        fetch(`/api/patient/${patientId}/${tableId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(item)
        }).catch(() => {});
    });
}

// ============================================================
// CÁLCULOS EN TIEMPO REAL
// ============================================================

// Utilidades de validación
function validateRange(value, min, max, fieldName) {
    if (!value && value !== 0) return { valid: false, message: `${fieldName} es requerido` };
    if (isNaN(value)) return { valid: false, message: `${fieldName} debe ser numérico` };
    if (min !== undefined && value < min) return { valid: false, message: `${fieldName} debe ser ≥ ${min}` };
    if (max !== undefined && value > max) return { valid: false, message: `${fieldName} debe ser ≤ ${max}` };
    return { valid: true };
}

function getFieldValue(name) {
    const field = document.querySelector(`[name="${name}"]`);
    if (!field) return null;
    const val = parseFloat(field.value);
    return isNaN(val) ? null : val;
}

function setFieldValue(name, value, decimals = 1) {
    const field = document.querySelector(`[name="${name}"]`);
    if (!field) return false;
    
    if (value !== null && !isNaN(value)) {
        field.value = decimals === 0 ? Math.round(value) : parseFloat(value.toFixed(decimals));
        
        // Efecto visual de actualización
        field.classList.add('field-updated');
        setTimeout(() => field.classList.remove('field-updated'), 500);
        
        return true;
    }
    return false;
}

// --------------------------------------------------
// 1. CÁLCULO DE TAM (Tensión Arterial Media)
// Fórmula: TAM = (TAS + 2 × TAD) / 3
// --------------------------------------------------
function calculateTAM() {
    const tas = getFieldValue('tas');
    const tad = getFieldValue('tad');
    
    if (tas === null || tad === null) return;
    
    // Validaciones
    const tasValidation = validateRange(tas, 50, 300, 'TAS');
    const tadValidation = validateRange(tad, 30, 200, 'TAD');
    
    if (!tasValidation.valid || !tadValidation.valid) return;
    if (tas <= tad) {
        showToast('TAS debe ser mayor que TAD', 'warning');
        return;
    }
    
    const tam = (tas + (2 * tad)) / 3;
    setFieldValue('tam', tam, 1);
}

// --------------------------------------------------
// 2. CÁLCULO DE IMC (Índice de Masa Corporal)
// Fórmula: IMC = peso / (talla²)
// Requiere: peso en kg, talla en metros
// --------------------------------------------------
function calculateIMC() {
    const peso = getFieldValue('peso');
    const talla = getFieldValue('talla');
    
    if (peso === null || talla === null) return;
    
    const pesoValidation = validateRange(peso, 10, 500, 'Peso');
    const tallaValidation = validateRange(talla, 0.5, 2.5, 'Talla');
    
    if (!pesoValidation.valid || !tallaValidation.valid) return;
    
    const imc = peso / (talla * talla);
    setFieldValue('imc', imc, 1);
    
    // También calcular peso ajustado si tenemos peso ideal
    calculatePesoAjustado();
}

// --------------------------------------------------
// 3. CÁLCULO DE PESO IDEAL
// Fórmula Broca modificada:
// - Hombres: 50 + 0.91 × (talla_cm - 152.4)
// - Mujeres: 45.5 + 0.91 × (talla_cm - 152.4)
// --------------------------------------------------
function calculatePesoIdeal() {
    const talla = getFieldValue('talla');
    const sexoField = document.querySelector('[name="sexo"]');
    const sexo = sexoField ? sexoField.value : '';
    
    if (talla === null || !sexo) return;
    
    const tallaValidation = validateRange(talla, 0.5, 2.5, 'Talla');
    if (!tallaValidation.valid) return;
    
    const tallaCm = talla * 100;
    let pesoIdeal;
    
    if (sexo === 'Masculino') {
        pesoIdeal = 50 + 0.91 * (tallaCm - 152.4);
    } else if (sexo === 'Femenino') {
        pesoIdeal = 45.5 + 0.91 * (tallaCm - 152.4);
    } else {
        return; // No calcular si no hay sexo definido
    }
    
    setFieldValue('peso_ideal', pesoIdeal, 1);
    
    // Recalcular peso ajustado
    calculatePesoAjustado();
}

// --------------------------------------------------
// 4. CÁLCULO DE PESO AJUSTADO
// Fórmula: Peso_ajustado = Peso_ideal + 0.4 × (Peso_real - Peso_ideal)
// --------------------------------------------------
function calculatePesoAjustado() {
    const peso = getFieldValue('peso');
    const pesoIdeal = getFieldValue('peso_ideal');
    
    if (peso === null || pesoIdeal === null) return;
    if (peso <= pesoIdeal) {
        // Si el peso real es menor o igual al ideal, usar peso real
        setFieldValue('peso_ajustado', peso, 1);
        return;
    }
    
    const pesoAjustado = pesoIdeal + 0.4 * (peso - pesoIdeal);
    setFieldValue('peso_ajustado', pesoAjustado, 1);
}

// --------------------------------------------------
// 5. CÁLCULO DE PA/Fi (Ratio PaO2/FiO2)
// Fórmula: PA/Fi = (pO2 / FiO2) × 100
// Requiere: pO2 en mmHg, FiO2 como % (21-100)
// --------------------------------------------------
function calculatePAFI() {
    const po2 = getFieldValue('gasometria_po2') || getFieldValue('po2');
    const fio2 = getFieldValue('fio2');
    
    if (po2 === null || fio2 === null) return;
    
    const po2Validation = validateRange(po2, 20, 700, 'pO2');
    const fio2Validation = validateRange(fio2, 21, 100, 'FiO2');
    
    if (!po2Validation.valid || !fio2Validation.valid) return;
    
    const pafi = (po2 / fio2) * 100;
    setFieldValue('pafi', pafi, 0);
}

// --------------------------------------------------
// 6. CÁLCULO DE EDAD
// A partir de fecha de nacimiento
// --------------------------------------------------
function calculateEdad() {
    const fechaNacField = document.querySelector('[name="fecha_nacimiento"]');
    if (!fechaNacField || !fechaNacField.value) return;
    
    const fechaNac = new Date(fechaNacField.value);
    const hoy = new Date();
    
    if (isNaN(fechaNac.getTime())) return;
    if (fechaNac > hoy) {
        showToast('La fecha de nacimiento no puede ser futura', 'warning');
        return;
    }
    
    let edad = hoy.getFullYear() - fechaNac.getFullYear();
    const mesDiff = hoy.getMonth() - fechaNac.getMonth();
    
    if (mesDiff < 0 || (mesDiff === 0 && hoy.getDate() < fechaNac.getDate())) {
        edad--;
    }
    
    setFieldValue('edad', edad, 0);
}

// --------------------------------------------------
// 7. CÁLCULO DE ÍNDICE URINARIO
// Fórmula: Diuresis / (Peso × Horas)
// Normalmente ml/kg/h
// --------------------------------------------------
function calculateIndiceUrinario() {
    const diuresis = getFieldValue('diuresis_total');
    const peso = getFieldValue('peso_estimado') || getFieldValue('peso') || getFieldValue('peso_ideal');
    const horas = getFieldValue('periodo_horas');
    
    if (diuresis === null || peso === null) return;
    
    let indiceUrinario;
    if (horas && horas > 0) {
        // ml/kg/h
        indiceUrinario = diuresis / (peso * horas);
    } else {
        // Solo ml/kg (sin tiempo especificado)
        indiceUrinario = diuresis / peso;
    }
    
    setFieldValue('indice_urinario', indiceUrinario, 2);
}

// --------------------------------------------------
// 8. CÁLCULO DE BALANCE HÍDRICO
// Balance = Ingresos - Egresos
// --------------------------------------------------
function calculateBalance() {
    const ingresos = getFieldValue('ingresos');
    const egresos = getFieldValue('egresos');
    
    if (ingresos === null || egresos === null) return;
    
    const balance = ingresos - egresos;
    setFieldValue('balance', balance, 0);
}

// --------------------------------------------------
// 9. CÁLCULOS NUTRICIONALES
// --------------------------------------------------
function calculateNutricion() {
    const volumen = getFieldValue('volumen_aporte');
    const kcal = getFieldValue('kcal_aporte');
    const proteinas = getFieldValue('proteinas_aporte');
    const peso = getFieldValue('peso') || getFieldValue('peso_estimado') || getFieldValue('peso_ideal');
    
    if (volumen === null || peso === null) return;
    
    // ml/24h (si ya es aporte de 24h, usar directo)
    const ml24h = volumen;
    setFieldValue('ml_24h_calc', ml24h, 1);
    
    // ml/h
    const mlH = ml24h / 24;
    setFieldValue('ml_h_calc', mlH, 1);
    
    // Kcal totales y Kcal/kg
    if (kcal !== null) {
        setFieldValue('kcal_totales_calc', kcal, 0);
        const kcalKg = kcal / peso;
        setFieldValue('kcal_kg_calc', kcalKg, 1);
    }
    
    // % Kcal (requeridas vs aportadas)
    const kcalReq = getFieldValue('kcal_requeridas');
    if (kcalReq !== null && kcal !== null && kcalReq > 0) {
        const pctKcal = (kcal / kcalReq) * 100;
        setFieldValue('pct_kcal_calc', pctKcal, 1);
    }
}

// ============================================================
// CÁLCULOS BACKEND (Escalas complejas)
// ============================================================

// Debounce para evitar llamadas excesivas
let apiDebounceTimer = null;

/**
 * Calcula escalas complejas llamando al backend
 * SOFA, APACHE II, NEWS2, SAPS3
 */
async function calculateScales() {
    const patientData = collectPatientData();
    
    // Mostrar estado de cálculo
    setScaleCalculating(true);
    
    try {
        const response = await fetch('/api/calculate/scores', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken()
            },
            body: JSON.stringify({
                type: 'scales',
                data: patientData
            })
        });
        
        if (!response.ok) throw new Error('Error en cálculo de escalas');
        
        const result = await response.json();
        
        if (result.success) {
            const scores = result.scores || {};
            
            // Actualizar campos con resultados
            // La estructura es scores.xxx.score donde xxx es el nombre de la escala
            if (scores.sofa?.score !== undefined) setFieldValue('sofa_ingreso', scores.sofa.score, 0);
            if (scores.sofa2?.score !== undefined) setFieldValue('sofa2_ingreso', scores.sofa2.score, 0);
            if (scores.apache2?.score !== undefined) setFieldValue('apache2_ingreso', scores.apache2.score, 0);
            if (scores.news2?.score !== undefined) setFieldValue('news2_ingreso', scores.news2.score, 0);
            if (scores.saps3?.score !== undefined) setFieldValue('saps3_ingreso', scores.saps3.score, 0);
            
            showToast('Escalas calculadas correctamente', 'success');
        } else {
            showToast(result.message || 'Error al calcular escalas', 'error');
        }
    } catch (error) {
        console.error('Error calculating scales:', error);
        showToast('Error al calcular escalas. Verifique los datos.', 'error');
    } finally {
        setScaleCalculating(false);
    }
}

/**
 * Recolecta datos del paciente del formulario
 */
function collectPatientData() {
    const form = document.getElementById('patientForm');
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    
    formData.forEach((value, key) => {
        // Intentar convertir números
        const numValue = parseFloat(value);
        data[key] = isNaN(numValue) ? value : numValue;
    });
    
    return data;
}

/**
 * Muestra/oculta indicador de cálculo en curso
 */
function setScaleCalculating(calculating) {
    const fields = ['sofa_ingreso', 'sofa2_ingreso', 'apache2_ingreso', 'news2_ingreso', 'saps3_ingreso'];
    
    fields.forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            if (calculating) {
                field.classList.add('calculating');
                field.dataset.previousValue = field.value;
                field.value = '...';
                field.disabled = true;
            } else {
                field.classList.remove('calculating');
                field.disabled = false;
                if (field.value === '...') {
                    field.value = field.dataset.previousValue || '';
                }
            }
        }
    });
}

// ============================================================
// INICIALIZACIÓN DE EVENT LISTENERS
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initRealTimeCalculations();
    initScaleCalculations();
});

/**
 * Inicializa todos los listeners para cálculos en tiempo real
 */
function initRealTimeCalculations() {
    // 1. TAM - TAS y TAD
    ['tas', 'tad'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculateTAM, 300));
            element.addEventListener('blur', calculateTAM);
        }
    });
    
    // 2. IMC - Peso y Talla
    ['peso', 'talla'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculateIMC, 300));
            element.addEventListener('blur', calculateIMC);
        }
    });
    
    // 3. Peso Ideal - Talla y Sexo
    const tallaElement = document.querySelector('[name="talla"]');
    const sexoElement = document.querySelector('[name="sexo"]');
    if (tallaElement) {
        tallaElement.addEventListener('input', debounce(calculatePesoIdeal, 300));
        tallaElement.addEventListener('blur', calculatePesoIdeal);
    }
    if (sexoElement) {
        sexoElement.addEventListener('change', calculatePesoIdeal);
    }
    
    // 4. PA/Fi - pO2 y FiO2
    ['gasometria_po2', 'po2', 'fio2'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculatePAFI, 300));
            element.addEventListener('blur', calculatePAFI);
        }
    });
    
    // 5. Edad - Fecha de nacimiento
    const fechaNacElement = document.querySelector('[name="fecha_nacimiento"]');
    if (fechaNacElement) {
        fechaNacElement.addEventListener('change', calculateEdad);
        fechaNacElement.addEventListener('blur', calculateEdad);
    }
    
    // 6. Índice Urinario - Diuresis, Peso, Periodo
    ['diuresis_total', 'peso_estimado', 'periodo_horas'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculateIndiceUrinario, 300));
            element.addEventListener('blur', calculateIndiceUrinario);
        }
    });
    
    // 7. Balance - Ingresos y Egresos
    ['ingresos', 'egresos'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculateBalance, 300));
            element.addEventListener('blur', calculateBalance);
        }
    });
    
    // 8. Nutrición - Campos relacionados
    ['volumen_aporte', 'kcal_aporte', 'proteinas_aporte', 'kcal_requeridas'].forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.addEventListener('input', debounce(calculateNutricion, 500));
        }
    });
    
    // Calcular valores iniciales si hay datos
    setTimeout(() => {
        calculateTAM();
        calculateIMC();
        calculatePesoIdeal();
        calculatePAFI();
        calculateEdad();
        calculateIndiceUrinario();
        calculateBalance();
        calculateNutricion();
    }, 100);
}

/**
 * Inicializa cálculo de escalas - Ahora el botón está en el HTML
 * y usa la función autoCalcularScores definida en el template
 */
function initScaleCalculations() {
    // El botón y la función autoCalcularScores ya están en patient_form.html
    // Esta función se mantiene por compatibilidad pero el cálculo real
    // se hace en el template con autoCalcularScores()
    console.log('Scale calculations initialized from HTML template');
}

/**
 * Debounce helper para limitar frecuencia de ejecución
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================
// NAVEGACIÓN DE TABS
// ============================================================

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    const selectedContent = document.getElementById(`tab-${tabName}`);
    const selectedTab = document.querySelector(`.tab[onclick="showTab('${tabName}')"]`) || 
                       document.querySelector(`.tab:nth-child(${getTabIndex(tabName)})`);
    
    if (selectedContent) selectedContent.classList.add('active');
    if (selectedTab) selectedTab.classList.add('active');
    
    // Save to URL hash
    window.location.hash = tabName;
}

function getTabIndex(tabName) {
    const order = ['datos', 'neurologico', 'hemodinamico', 'ventilatorio', 'hidrico', 'gastro', 'hematologia', 'evaluacion'];
    return order.indexOf(tabName) + 1;
}

// Load tab from hash
document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.replace('#', '');
    if (hash) {
        showTab(hash);
    }
});

// CSRF Token helper
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// Exportar funciones para uso global
window.SinapsidCalculations = {
    calculateTAM,
    calculateIMC,
    calculatePesoIdeal,
    calculatePAFI,
    calculateEdad,
    calculateIndiceUrinario,
    calculateBalance,
    calculateNutricion,
    calculateScales
};
