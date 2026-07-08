/**
 * Sistema de Tablas Dinámicas
 * Permite agregar múltiples filas a las tablas de medicamentos
 */

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
        types: ['select', 'date', 'select', 'text', 'tags', 'tags'],
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
 * Crea el datalist de microorganismos si no existe
 */
function ensureMicroorganismosDatalist() {
    if (document.getElementById('microorganismos_list')) return;
    
    const datalist = document.createElement('datalist');
    datalist.id = 'microorganismos_list';
    const microorganismos = [
        'ESCHERICHIA COLI',
        'KLEBSIELLA PNEUMONIAE',
        'KLEBSIELLA OXYTOCA',
        'PSEUDOMONAS AERUGINOSA',
        'STAPHYLOCOCCUS AUREUS (MSSA)',
        'STAPHYLOCOCCUS AUREUS (MRSA)',
        'STAPHYLOCOCCUS EPIDERMIDIS',
        'ENTEROCOCCUS FAECALIS',
        'ENTEROCOCCUS FAECIUM (VRE)',
        'ACINETOBACTER BAUMANNII',
        'CANDIDA ALBICANS',
        'CANDIDA PARAPSILOSIS',
        'CANDIDA GLABRATA',
        'CANDIDA AURIS',
        'CANDIDA TROPICALIS',
        'PROTEUS MIRABILIS',
        'SERRATIA MARCESCENS',
        'ENTEROBACTER CLOACAE',
        'CITROBACTER FREUNDII',
        'STREPTOCOCCUS PNEUMONIAE',
        'HAEMOPHILUS INFLUENZAE',
        'LEGIONELLA PNEUMOPHILA',
        'ASPERGILLUS FUMIGATUS',
        'ASPERGILLUS FLAVUS',
        'STENOTROPHOMONAS MALTOPHILIA',
        'BURKHOLDERIA CEPACIA',
        'CLOSTRIDIOIDES DIFFICILE',
        'MORGANELLA MORGANII',
        'PROVIDENCIA STUARTII',
        'SALMONELLA ENTERICA',
        'SHIGELLA SPP',
        'NEISSERIA MENINGITIDIS',
        'LISTERIA MONOCYTOGENES',
        'MYCOBACTERIUM TUBERCULOSIS',
        'PNEUMOCYSTIS JIROVECII'
    ];
    datalist.innerHTML = microorganismos.map(m => `<option value="${m}">`).join('');
    document.body.appendChild(datalist);
}

/**
 * Diccionario de antimicrobianos para autocompletado
 */
const ANTIMICROBIANOS_DICT = [
    // Betalactámicos
    'AMPICILINA', 'AMOXICILINA', 'AMOXICILINA/ACIDO CLAVULANICO',
    'PIPERACILINA/TAZOBACTAM', 'TICARCILINA/ACIDO CLAVULANICO',
    'CEFAZOLINA', 'CEFUROXIMA', 'CEFTRIAXONA', 'CEFOTAXIMA', 'CEFEPIME',
    'CEFTAZIDIMA', 'CEFEPIME', 'ERTAPENEM', 'IMIPENEM', 'MEROPENEM', 'DORIPENEM',
    'AZTREONAM',
    // Aminoglucósidos
    'GENTAMICINA', 'AMIKACINA', 'TOBRAMICINA', 'NETILMICINA',
    // Fluoroquinolonas
    'CIPROFLOXACINO', 'LEVOFLOXACINO', 'MOXIFLOXACINO', 'NORFLOXACINO',
    // Macrólidos
    'AZITROMICINA', 'CLARITROMICINA', 'ERITROMICINA',
    // Glicopéptidos
    'VANCOMICINA', 'TEICOPLANINA',
    // Lipopéptidos
    'DAPTOMICINA',
    // Oxazolidinonas
    'LINEZOLID',
    // Fórmicos
    'COLISTINA', 'POLIMIXINA B',
    // Sulfonamidas
    'TRIMETOPRIM/SULFAMETOXAZOL',
    // Nitroimidazoles
    'METRONIDAZOL',
    // Otros antibacterianos
    'CLINDAMICINA', 'CLORFENICOL', 'FOSFOMICINA', 'TIGECICLINA',
    // Antifúngicos
    'ANFOTERICINA B', 'ANFOTERICINA B LIPOSOMAL',
    'FLUCONAZOL', 'ITRACONAZOL', 'VORICONAZOL', 'POSACONAZOL', 'ISAVUCONAZOL',
    'CASPOFUNGINA', 'MICAFUNGINA', 'ANIDULAFUNGINA',
    'FLUCITOSINA',
    // Antivirales
    'ACICLOVIR', 'VALACICLOVIR',
    'GANCI CLOVIR', 'VALGANCI CLOVIR',
    'FOSCARNET', 'CIDOFOVIR',
    'OSELTAMIVIR', 'ZANAMIVIR',
    // Antituberculosos
    'ISONIAZIDA', 'RIFAMPICINA', 'PIRAZINAMIDA', 'ETAMBUTOL', 'ESTREPTOMICINA'
];

/**
 * Crea un campo tipo tags para sensibilidad/resistencia
 */
function createTagsField(container, fieldName, placeholder) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tags-field-wrapper';
    wrapper.style.cssText = 'border: 1px solid var(--border); border-radius: 4px; padding: 8px; min-height: 40px; background: var(--bg); cursor: text; display: flex; flex-wrap: wrap; gap: 5px; align-items: center;';
    
    // Input oculto para guardar el valor
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = fieldName;
    wrapper.appendChild(hiddenInput);
    
    // Input visible para escribir
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = placeholder || 'Escribir y presionar Enter...';
    input.style.cssText = 'border: none; outline: none; background: transparent; flex: 1; min-width: 150px; color: var(--text);';
    
    // Datalist para sugerencias
    const datalistId = `antimicrobianos-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const datalist = document.createElement('datalist');
    datalist.id = datalistId;
    datalist.innerHTML = ANTIMICROBIANOS_DICT.map(a => `<option value="${a}">`).join('');
    document.body.appendChild(datalist);
    input.setAttribute('list', datalistId);
    
    // Contenedor de tags
    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'tags-container';
    tagsContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 5px; width: 100%;';
    wrapper.insertBefore(tagsContainer, input);
    
    // Array para mantener los tags
    let tags = [];
    
    // Función para actualizar el valor oculto
    function updateHiddenValue() {
        hiddenInput.value = tags.join(', ');
    }
    
    // Función para crear un tag visual
    function createTag(text) {
        const tag = document.createElement('span');
        tag.className = 'antimicrobiano-tag';
        tag.style.cssText = 'background: var(--accent); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 5px;';
        tag.innerHTML = `${text} <span style="cursor: pointer; font-weight: bold;">×</span>`;
        
        // Evento para eliminar tag
        tag.querySelector('span').onclick = () => {
            tags = tags.filter(t => t !== text);
            tag.remove();
            updateHiddenValue();
        };
        
        return tag;
    }
    
    // Evento al presionar Enter
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const value = input.value.trim();
            if (value && !tags.includes(value)) {
                tags.push(value);
                tagsContainer.appendChild(createTag(value));
                updateHiddenValue();
                input.value = '';
            }
        }
    });
    
    // Evento al seleccionar de datalist
    input.addEventListener('change', () => {
        const value = input.value.trim();
        if (value && !tags.includes(value)) {
            tags.push(value);
            tagsContainer.appendChild(createTag(value));
            updateHiddenValue();
            input.value = '';
        }
    });
    
    // Click en wrapper enfoca el input
    wrapper.addEventListener('click', (e) => {
        if (e.target === wrapper) {
            input.focus();
        }
    });
    
    wrapper.appendChild(input);
    
    return { wrapper, hiddenInput, getTags: () => tags };
}

/**
 * Actualiza el valor oculto de un campo tags cuando se elimina una etiqueta
 */
function updateTagsHiddenValue(wrapper) {
    const tagsContainer = wrapper.querySelector('.tags-container');
    const hiddenInput = wrapper.querySelector('input[type="hidden"]');
    if (!tagsContainer || !hiddenInput) return;
    
    const tags = [];
    tagsContainer.querySelectorAll('.antimicrobiano-tag').forEach(tag => {
        // Obtener el texto sin el botón de cerrar
        const text = tag.childNodes[0].textContent.trim();
        if (text) tags.push(text);
    });
    
    hiddenInput.value = tags.join(', ');
}

/**
 * Inicializa el sistema de tablas dinámicas
 */
function initDynamicTables() {
    // Crear datalist de microorganismos
    ensureMicroorganismosDatalist();
    
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
    // Buscar todos los inputs que coincidan con el nombre de la tabla
    const inputs = document.querySelectorAll(`input[name*="${tableName}"], select[name*="${tableName}"]`);
    if (!inputs.length) return null;

    // Para cada input encontrado, buscar su contenedor card-body más cercano
    for (const input of inputs) {
        const cardBody = input.closest('.card-body');
        if (cardBody) {
            // Verificar que este card-body realmente contenga inputs de esta tabla
            const hasTableInputs = cardBody.querySelector(`input[name*="${tableName}"], select[name*="${tableName}"]`);
            if (hasTableInputs) {
                return cardBody;
            }
        }
    }

    // Fallback: buscar por id del tab
    const tabPanel = document.querySelector(`div[id*="${tableName}"], div[data-table="${tableName}"]`);
    if (tabPanel) return tabPanel;

    return null;
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

    // Agregar botones de acción a la fila estática existente
    const row = section.querySelector('.section-grid');
    if (row) {
        row.style.position = 'relative';
        addActionButtons(row, tableName, 0);
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
    newRow.style.cssText = 'grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 15px; padding-top: 15px; border-top: 1px dashed var(--border); position: relative;';
    newRow.dataset.index = index;
    newRow.dataset.mode = 'edit'; // Modo: edit (editable) o view (solo lectura)

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
        let tagsWrapper = null;
        
        if (config.types[i] === 'tags') {
            // Campo tipo tags para sensibilidad/resistencia
            const tagsField = createTagsField(
                formGroup,
                `dynamic_${tableName}[${index}][${field}]`,
                config.placeholders[i]
            );
            tagsWrapper = tagsField.wrapper;
            input = tagsField.hiddenInput;
            formGroup.appendChild(tagsWrapper);
        } else if (config.types[i] === 'select' && config.options && config.options[field]) {
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

        if (config.types[i] !== 'tags') {
            input.name = `dynamic_${tableName}[${index}][${field}]`;
            input.placeholder = config.placeholders[i] || '';
            input.className = 'form-control';
            
            // Agregar autocomplete para campo medicamento
            if (field === 'medicamento') {
                setupMedicationAutocomplete(input, tableName);
            }
            
            // Agregar datalist para microorganismo en cultivos
            if (tableName === 'cultivos' && field === 'microorganismo') {
                input.setAttribute('list', 'microorganismos_list');
                input.setAttribute('placeholder', 'Seleccionar o escribir...');
            }

            formGroup.appendChild(input);
        }
        
        newRow.appendChild(formGroup);
    });

    // Agregar botones de acción (editar y eliminar)
    addActionButtons(newRow, tableName, index);

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
 * Agrega botones de acción a una fila (editar y eliminar)
 */
function addActionButtons(row, tableName, index) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'row-actions';
    actionsDiv.style.cssText = 'position: absolute; right: 5px; top: 5px; display: flex; gap: 5px; z-index: 10;';

    // Botón de editar/guardar
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.innerHTML = '✏️';
    editBtn.title = 'Guardar/Editar fila';
    editBtn.className = 'btn-edit-row';
    editBtn.style.cssText = 'background: transparent; border: none; cursor: pointer; font-size: 0.9rem; opacity: 0.6; padding: 2px 5px; border-radius: 3px; transition: all 0.2s;';
    editBtn.onmouseover = () => { editBtn.style.opacity = '1'; editBtn.style.background = 'rgba(255, 107, 53, 0.2)'; };
    editBtn.onmouseout = () => { editBtn.style.opacity = '0.6'; editBtn.style.background = 'transparent'; };
    editBtn.onclick = () => toggleRowEditMode(row, editBtn);

    // Botón de eliminar
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.innerHTML = '❌';
    deleteBtn.title = 'Eliminar fila';
    deleteBtn.className = 'btn-delete-row';
    deleteBtn.style.cssText = 'background: transparent; border: none; cursor: pointer; font-size: 0.9rem; opacity: 0.6; padding: 2px 5px; border-radius: 3px; transition: all 0.2s;';
    deleteBtn.onmouseover = () => { deleteBtn.style.opacity = '1'; deleteBtn.style.background = 'rgba(220, 38, 38, 0.2)'; };
    deleteBtn.onmouseout = () => { deleteBtn.style.opacity = '0.6'; deleteBtn.style.background = 'transparent'; };
    deleteBtn.onclick = () => deleteRow(row, tableName);

    actionsDiv.appendChild(editBtn);
    actionsDiv.appendChild(deleteBtn);
    row.appendChild(actionsDiv);
}

/**
 * Alterna entre modo edición y modo vista para una fila
 */
function toggleRowEditMode(row, btn) {
    const isEditMode = row.dataset.mode === 'edit';
    const inputs = row.querySelectorAll('input, select');
    
    if (isEditMode) {
        // Cambiar a modo vista (solo lectura)
        inputs.forEach(input => {
            input.dataset.previousValue = input.value;
            input.setAttribute('readonly', true);
            if (input.tagName === 'SELECT') {
                input.setAttribute('disabled', true);
            }
            input.style.background = 'transparent';
            input.style.border = 'none';
            input.style.cursor = 'default';
        });
        row.dataset.mode = 'view';
        btn.innerHTML = '✏️';
        btn.title = 'Editar fila';
        row.style.opacity = '0.85';
    } else {
        // Cambiar a modo edición
        inputs.forEach(input => {
            input.removeAttribute('readonly');
            if (input.tagName === 'SELECT') {
                input.removeAttribute('disabled');
            }
            input.style.background = '';
            input.style.border = '';
            input.style.cursor = '';
        });
        row.dataset.mode = 'edit';
        btn.innerHTML = '💾';
        btn.title = 'Guardar fila';
        row.style.opacity = '1';
    }
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

/**
 * Edita una fila guardada en la base de datos
 * Convierte la fila de la tabla en campos editables
 */
function editSavedRow(btn, tableName, itemId) {
    const row = btn.closest('tr');
    if (!row) return;

    // Verificar si ya está en modo edición
    if (row.dataset.editing === 'true') {
        // Guardar cambios
        saveEditedRow(row, tableName, itemId);
        return;
    }

    // Activar modo edición
    row.dataset.editing = 'true';
    btn.innerHTML = '💾';
    btn.title = 'Guardar cambios';

    // Obtener todas las celdas de datos (excluyendo la columna de acciones)
    const cells = row.querySelectorAll('td:not(:last-child)');
    
    cells.forEach((cell, index) => {
        const currentValue = cell.textContent.trim() === '-' ? '' : cell.textContent.trim();
        const fieldName = getFieldNameForColumn(tableName, index);
        
        if (fieldName) {
            // Crear input según el tipo de campo
            let input;
            
            if (fieldName === 'tipo' || fieldName === 'resultado') {
                input = document.createElement('select');
                input.className = 'form-control';
                input.style.cssText = 'width: 100%; padding: 4px; border: 1px solid var(--border); border-radius: 3px; font-size: 0.9rem;';
                
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = 'Seleccionar...';
                input.appendChild(emptyOption);
                
                if (fieldName === 'tipo') {
                    ['Hemocultivo', 'Urocultivo', 'CSB (Secreción Bronquial)', 'LCR (Líquido Cefalorraquídeo)', 'Coprocultivo', 'Cultivo de Herida', 'Dispositivo Invasivo (CVC, SNG, ETT)', 'Otros'].forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt;
                        option.textContent = opt;
                        if (opt === currentValue) option.selected = true;
                        input.appendChild(option);
                    });
                } else if (fieldName === 'resultado') {
                    ['Negativo', 'Positivo', 'Pendiente'].forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt;
                        option.textContent = opt;
                        if (opt === currentValue) option.selected = true;
                        input.appendChild(option);
                    });
                }
            } else if (fieldName === 'sensibilidad' || fieldName === 'resistencia') {
                // Campo tipo tags para edición
                const tagsField = createTagsField(
                    cell,
                    `edit_${tableName}[${itemId}][${fieldName}]`,
                    'Escribir y presionar Enter...'
                );
                
                // Parsear valor existente (formato: "ANTIBIOTICO1, ANTIBIOTICO2")
                if (currentValue) {
                    const existingTags = currentValue.split(',').map(t => t.trim()).filter(t => t);
                    existingTags.forEach(tagText => {
                        tagsField.getTags().push(tagText);
                        const tag = document.createElement('span');
                        tag.className = 'antimicrobiano-tag';
                        tag.style.cssText = 'background: var(--accent); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 5px; margin: 2px;';
                        tag.innerHTML = `${tagText} <span style="cursor: pointer; font-weight: bold;" onclick="this.parentElement.remove(); updateTagsHiddenValue(this.closest('.tags-field-wrapper'));">×</span>`;
                        tagsField.wrapper.querySelector('.tags-container').appendChild(tag);
                    });
                    tagsField.hiddenInput.value = currentValue;
                }
                
                cell.innerHTML = '';
                cell.appendChild(tagsField.wrapper);
                return; // Skip normal input handling
            } else if (fieldName === 'fecha') {
                input = document.createElement('input');
                input.type = 'date';
                input.className = 'form-control';
                input.style.cssText = 'width: 100%; padding: 4px; border: 1px solid var(--border); border-radius: 3px; font-size: 0.9rem;';
                input.value = currentValue;
            } else {
                input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control';
                input.style.cssText = 'width: 100%; padding: 4px; border: 1px solid var(--border); border-radius: 3px; font-size: 0.9rem;';
                input.value = currentValue;
                
                if (fieldName === 'microorganismo') {
                    input.setAttribute('list', 'microorganismos_list');
                    input.setAttribute('onblur', 'this.value = normalizeToUpper(this.value)');
                }
            }
            
            input.name = `edit_${tableName}[${itemId}][${fieldName}]`;
            cell.innerHTML = '';
            cell.appendChild(input);
        }
    });
}

/**
 * Obtiene el nombre del campo según la tabla y el índice de columna
 */
function getFieldNameForColumn(tableName, columnIndex) {
    const fieldMap = {
        'cultivos': ['tipo', 'fecha', 'resultado', 'microorganismo', 'sensibilidad', 'resistencia']
    };
    
    const fields = fieldMap[tableName];
    return fields ? fields[columnIndex] : null;
}

/**
 * Guarda los cambios de una fila editada
 */
function saveEditedRow(row, tableName, itemId) {
    const inputs = row.querySelectorAll('input, select');
    const data = { id: itemId };
    
    inputs.forEach(input => {
        const match = input.name.match(/\[(\w+)\]$/);
        if (match) {
            data[match[1]] = input.value;
        }
    });

    // Enviar al servidor
    fetch(`/api/dynamic/${tableName}/${itemId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Recargar la página para mostrar los datos actualizados
            window.location.reload();
        } else {
            alert('Error al guardar: ' + (result.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al guardar los cambios');
    });
}

/**
 * Elimina una fila guardada de la base de datos
 */
function deleteSavedRow(btn, tableName, itemId) {
    if (!confirm('¿Eliminar este registro permanentemente?')) return;

    fetch(`/api/dynamic/${tableName}/${itemId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Eliminar la fila visualmente con animación
            const row = btn.closest('tr');
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '0';
            row.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                row.remove();
            }, 300);
        } else {
            alert('Error al eliminar: ' + (result.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al eliminar el registro');
    });
}
