/**
 * Sistema de Tablas Dinámicas
 * Permite agregar múltiples filas a las tablas de medicamentos
 */

// Función para normalizar texto a mayúsculas
function normalizeToUpper(value) {
    if (!value || typeof value !== 'string') return '';
    return value.trim().toUpperCase();
}

// Configuración de las tablas dinámicas
const DYNAMIC_TABLES_CONFIG = {
    'medicamentos_neurologicos': {
        fields: ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin', 'indicacion'],
        labels: ['Medicamento', 'Unidad', 'Dosis', 'Fecha Inicio', 'Fecha Fin', 'Indicación'],
        placeholders: ['Ej: Midazolam', 'Ej: mg', 'Ej: 2-5', '', '', 'Ej: Sedación'],
        types: ['text', 'text', 'text', 'date', 'date', 'text']
    },
    'medicamentos_hemodinamicos': {
        fields: ['medicamento', 'unidad', 'dosis_max', 'dosis_min', 'fecha_inicio', 'fecha_fin', 'indicacion'],
        labels: ['Medicamento', 'Unidad', 'Dosis Max', 'Dosis Min', 'Fecha Inicio', 'Fecha Fin', 'Indicación'],
        placeholders: ['Ej: Noradrenalina', 'Ej: mcg/min', 'Ej: 1.0', 'Ej: 0.1', '', '', 'Ej: Choque'],
        types: ['text', 'text', 'text', 'text', 'date', 'date', 'text']
    },
    'medicamentos_nefro': {
        fields: ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
        labels: ['Medicamento', 'Unidad', 'Dosis', 'Fecha Inicio', 'Fecha Fin'],
        placeholders: ['Ej: Furosemida', 'Ej: mg', 'Ej: 20-40', '', ''],
        types: ['text', 'text', 'text', 'date', 'date']
    },
    'medicamentos_gastro': {
        fields: ['medicamento', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
        labels: ['Medicamento', 'Unidad', 'Dosis', 'Fecha Inicio', 'Fecha Fin'],
        placeholders: ['Ej: Omeprazol', 'Ej: mg', 'Ej: 20-40', '', ''],
        types: ['text', 'text', 'text', 'date', 'date']
    },
    'medicacion_hematologica': {
        fields: ['medicamento', 'dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion'],
        labels: ['Medicamento', 'Dosis', 'Unidad', 'Fecha Inicio', 'Fecha Fin', 'Indicación'],
        placeholders: ['Ej: Heparina', 'Ej: 5000', 'Ej: UI', '', '', 'Ej: Profilaxis'],
        types: ['text', 'text', 'text', 'date', 'date', 'text']
    },
    'cultivos': {
        fields: ['tipo', 'fecha', 'resultado', 'microorganismo', 'sensibilidad', 'resistencia'],
        labels: ['Tipo', 'Fecha', 'Resultado', 'Microorganismo', 'Sensibilidad', 'Resistencia'],
        placeholders: ['', '', '', 'Seleccionar o escribir...', 'Escribir antibiótico y presionar Enter...', 'Escribir antibiótico y presionar Enter...'],
        types: ['select', 'date', 'select', 'text', 'text', 'text'],
        options: {
            'tipo': ['Hemocultivo', 'Urocultivo', 'CSB (Secreción Bronquial)', 'LCR (Líquido Cefalorraquídeo)', 'Coprocultivo', 'Cultivo de Herida', 'Dispositivo Invasivo (CVC, SNG, ETT)', 'Otros'],
            'resultado': ['Positivo', 'Negativo', 'Pendiente']
        }
    },
    'transfusiones': {
        fields: ['componente', 'dosis_unidades', 'dosis_ml', 'fecha_transfusion', 'reaccion_adversa'],
        labels: ['Componente', 'Unidades', 'Volumen (ml)', 'Fecha', 'Reacción Adversa'],
        placeholders: ['', 'Ej: 2', 'Ej: 450', '', 'Ej: Ninguna'],
        types: ['select', 'number', 'number', 'date', 'text'],
        options: {
            'componente': ['glóbulos rojos', 'plaquetas', 'plasma fresco', 'crioprecipitados', 'albumina']
        }
    }
};

// Contadores para cada tabla
const rowCounters = {};

/**
 * Inicializa el sistema de tablas dinámicas
 */
function initDynamicTables() {
    Object.keys(DYNAMIC_TABLES_CONFIG).forEach(tableName => {
        // Encontrar el contenedor de la tabla
        const container = findTableContainer(tableName);
        if (!container) return;

        // Inicializar contador
        rowCounters[tableName] = countExistingRows(container);

        // Agregar botón "+ Agregar" después de la tabla existente
        addAddButton(container, tableName);

        // Convertir fila estática en dinámica si existe
        convertStaticRow(container, tableName);
    });
}

/**
 * Encuentra el contenedor de una tabla
 */
function findTableContainer(tableName) {
    // Buscar por el nombre del campo en el formulario
    const input = document.querySelector(`input[name*="${tableName}"], select[name*="${tableName}"]`);
    if (!input) return null;

    // Subir hasta encontrar el card-body o contenedor principal
    let element = input.closest('.card-body');
    if (!element) {
        element = input.closest('.dynamic-form-section');
    }
    if (!element) {
        element = input.closest('div[id*="tab-"]');
    }

    return element;
}

/**
 * Cuenta las filas existentes
 */
function countExistingRows(container) {
    const inputs = container.querySelectorAll('input[name*="["], select[name*="["]');
    const indices = new Set();
    inputs.forEach(input => {
        const match = input.name.match(/\[(\d+)\]/);
        if (match) indices.add(parseInt(match[1]));
    });
    return indices.size;
}

/**
 * Agrega el botón de agregar fila
 */
function addAddButton(container, tableName) {
    const config = DYNAMIC_TABLES_CONFIG[tableName];
    
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'dynamic-table-actions';
    buttonContainer.style.cssText = 'margin-top: 15px; text-align: center;';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-secondary';
    button.innerHTML = '➕ Agregar ' + getTableLabel(tableName);
    button.onclick = () => addNewRow(container, tableName);

    buttonContainer.appendChild(button);
    
    // Insertar después de la sección de formulario dinámico
    const formSection = container.querySelector('.dynamic-form-section');
    if (formSection) {
        formSection.parentNode.insertBefore(buttonContainer, formSection.nextSibling);
    } else {
        container.appendChild(buttonContainer);
    }
}

/**
 * Obtiene la etiqueta legible de la tabla
 */
function getTableLabel(tableName) {
    const labels = {
        'medicamentos_neurologicos': 'Medicamento Neurológico',
        'medicamentos_hemodinamicos': 'Medicamento Hemodinámico',
        'medicamentos_nefro': 'Medicamento Nefrólogo',
        'medicamentos_gastro': 'Medicamento Gastro',
        'medicacion_hematologica': 'Medicación Hematológica',
        'cultivos': 'Cultivo',
        'transfusiones': 'Transfusión'
    };
    return labels[tableName] || 'Registro';
}

/**
 * Convierte la fila estática existente en parte del sistema dinámico
 */
function convertStaticRow(container, tableName) {
    const section = container.querySelector('.dynamic-form-section');
    if (!section) return;

    // Agregar botón de eliminar a la fila existente
    const row = section.querySelector('.section-grid');
    if (row) {
        addDeleteButton(row, tableName, 0);
    }
}

/**
 * Agrega una nueva fila a la tabla
 */
function addNewRow(container, tableName) {
    const config = DYNAMIC_TABLES_CONFIG[tableName];
    if (!config) return;

    const index = rowCounters[tableName]++;
    const section = container.querySelector('.dynamic-form-section');
    
    if (!section) return;

    // Crear nueva fila
    const newRow = document.createElement('div');
    newRow.className = 'section-grid dynamic-row';
    newRow.style.cssText = 'grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 15px; padding-top: 15px; border-top: 1px dashed var(--border);';
    newRow.dataset.index = index;

    // Crear campos
    config.fields.forEach((field, i) => {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';
        
        if (field === 'indicacion' || field === 'sensibilidad' || field === 'resistencia') {
            formGroup.style.gridColumn = 'span 2';
        }

        const label = document.createElement('label');
        label.textContent = config.labels[i];
        formGroup.appendChild(label);

        let input;
        if (config.types[i] === 'select' && config.options && config.options[field]) {
            input = document.createElement('select');
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'Seleccionar...';
            input.appendChild(emptyOption);
            
            config.options[field].forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt.charAt(0).toUpperCase() + opt.slice(1);
                input.appendChild(option);
            });
        } else {
            input = document.createElement('input');
            input.type = config.types[i];
        }

        input.name = `dynamic_${tableName}[${index}][${field}]`;
        input.placeholder = config.placeholders[i] || '';
        
        // Agregar autocomplete para campo medicamento
        if (field === 'medicamento') {
            setupMedicationAutocomplete(input, tableName);
        }

        formGroup.appendChild(input);
        newRow.appendChild(formGroup);
    });

    // Agregar botón de eliminar
    addDeleteButton(newRow, tableName, index);

    // Insertar la nueva fila
    section.appendChild(newRow);

    // Animación de entrada
    newRow.style.opacity = '0';
    newRow.style.transform = 'translateY(-10px)';
    newRow.style.transition = 'all 0.3s ease';
    
    setTimeout(() => {
        newRow.style.opacity = '1';
        newRow.style.transform = 'translateY(0)';
    }, 10);
}

/**
 * Agrega botón de eliminar a una fila
 */
function addDeleteButton(row, tableName, index) {
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.innerHTML = '❌';
    deleteBtn.title = 'Eliminar fila';
    deleteBtn.style.cssText = `
        position: absolute;
        right: 10px;
        top: 10px;
        background: transparent;
        border: none;
        color: var(--danger);
        cursor: pointer;
        font-size: 1rem;
        opacity: 0.6;
        transition: opacity 0.2s;
    `;
    deleteBtn.onmouseover = () => deleteBtn.style.opacity = '1';
    deleteBtn.onmouseout = () => deleteBtn.style.opacity = '0.6';
    deleteBtn.onclick = () => deleteRow(row, tableName);

    row.style.position = 'relative';
    row.appendChild(deleteBtn);
}

/**
 * Elimina una fila
 */
function deleteRow(row, tableName) {
    if (!confirm('¿Eliminar este registro?')) return;

    row.style.opacity = '0';
    row.style.transform = 'translateX(-20px)';
    
    setTimeout(() => {
        row.remove();
        // Reordenar índices
        reindexRows(tableName);
    }, 300);
}

/**
 * Reordena los índices después de eliminar
 */
function reindexRows(tableName) {
    const container = findTableContainer(tableName);
    if (!container) return;

    const rows = container.querySelectorAll('.dynamic-row');
    rows.forEach((row, newIndex) => {
        const inputs = row.querySelectorAll('input, select');
        inputs.forEach(input => {
            const oldName = input.name;
            const newName = oldName.replace(/\[\d+\]/, `[${newIndex}]`);
            input.name = newName;
        });
        row.dataset.index = newIndex;
    });

    rowCounters[tableName] = rows.length;
}

/**
 * Configura el autocompletado para un campo de medicamento
 */
function setupMedicationAutocomplete(input, tableName) {
    // Mapear nombres de tabla a especialidad del diccionario
    const specialtyMap = {
        'medicamentos_neurologicos': 'neurologicos',
        'medicamentos_hemodinamicos': 'hemodinamicos',
        'medicamentos_nefro': 'nefro',
        'medicamentos_gastro': 'gastro',
        'medicacion_hematologica': 'hematologica'
    };

    const specialty = specialtyMap[tableName];
    if (!specialty || typeof MEDICATION_DICTIONARY === 'undefined') return;

    const dictionary = MEDICATION_DICTIONARY[specialty];
    if (!dictionary) return;

    // Crear datalist
    const datalistId = `meds-${specialty}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    let datalist = document.getElementById(datalistId);
    
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = datalistId;
        document.body.appendChild(datalist);
    }

    const medications = Object.keys(dictionary);
    datalist.innerHTML = medications.map(med => `<option value="${med}">`).join('');
    input.setAttribute('list', datalistId);

    // Evento al seleccionar
    input.addEventListener('change', function() {
        const value = input.value.trim();
        if (dictionary[value]) {
            autoFillRelatedFields(input, dictionary[value], tableName);
        }
    });
}

/**
 * Rellena campos relacionados desde el diccionario
 */
function autoFillRelatedFields(input, data, tableName) {
    const row = input.closest('.section-grid');
    if (!row) return;

    const inputs = row.querySelectorAll('input, select');
    
    inputs.forEach(field => {
        const nameMatch = field.name.match(/\[([^\]]+)\]$/);
        if (!nameMatch) return;
        
        const fieldName = nameMatch[1];
        if (data[fieldName] && field !== input) {
            field.value = data[fieldName];
            field.style.backgroundColor = 'rgba(255, 107, 53, 0.2)';
            setTimeout(() => {
                field.style.backgroundColor = '';
            }, 800);
        }
    });

    // Fecha de inicio por defecto
    const fechaInicio = row.querySelector('input[name*="[fecha_inicio]"]');
    if (fechaInicio && !fechaInicio.value) {
        fechaInicio.value = new Date().toISOString().split('T')[0];
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initDynamicTables);

// Exponer función global
window.initDynamicTables = initDynamicTables;
window.addNewRow = addNewRow;
