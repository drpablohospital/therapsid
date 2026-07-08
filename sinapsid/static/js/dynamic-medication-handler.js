/**
 * Manejador de Tablas Dinámicas de Medicamentos v2.0
 * - Normalización a MAYÚSCULAS sin acentos
 * - Select de vía de administración con unidades dinámicas
 * - Autocompletado con diccionario v2
 */

(function() {
    'use strict';

    // Mapa de especialidades
    const SPECIALTY_MAP = {
        'medicamentos_neurologicos': 'neurologicos',
        'medicamentos_hemodinamicos': 'hemodinamicos',
        'medicamentos_nefro': 'nefro',
        'medicamentos_gastro': 'gastro',
        'medicacion_hematologica': 'hematologica'
    };

    // Contadores para índices
    const counters = {};

    /**
     * Inicializa todos los manejadores de medicamentos
     */
    function initMedicationHandlers() {
        console.log('[MED-HANDLER] Inicializando...');
        console.log('[MED-HANDLER] MEDICATION_DICTIONARY_V2 disponible:', typeof MEDICATION_DICTIONARY_V2 !== 'undefined');
        
        // Inicializar contadores
        Object.keys(SPECIALTY_MAP).forEach(key => {
            counters[key] = 0;
        });

        // Configurar autocompletado
        setupAutocompleteForAll();
        
        // Configurar normalización
        setupNormalization();
        
        // Configurar manejo de vías
        setupViaHandlers();
        
        console.log('[MED-HANDLER] Inicialización completa');
    }

    /**
     * Configura autocompletado para todos los campos de medicamento
     */
    function setupAutocompleteForAll() {
        console.log('[MED-HANDLER] Configurando autocompletado...');
        document.querySelectorAll('input[name*="[medicamento]"]').forEach(input => {
            const match = input.name.match(/dynamic_(medicamentos_[a-z_]+|medicacion_[a-z_]+)\[(\d+)\]/);
            if (!match) {
                console.log('[MED-HANDLER] No match para:', input.name);
                return;
            }
            
            const tableName = match[1];
            const specialty = SPECIALTY_MAP[tableName];
            if (!specialty || !MEDICATION_DICTIONARY_V2[specialty]) {
                console.log('[MED-HANDLER] No specialty/diccionario para:', tableName);
                return;
            }

            console.log('[MED-HANDLER] Configurado:', tableName, '->', specialty);
            const dictionary = MEDICATION_DICTIONARY_V2[specialty];
            setupAutocomplete(input, dictionary, specialty, match[2]);
        });
    }

    /**
     * Configura autocompletado para un input específico
     */
    function setupAutocomplete(input, dictionary, specialty, index) {
        const datalistId = `meds-${specialty}-${index}`;
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
            const normalizedName = normalizeMedicationName(this.value);
            if (dictionary[normalizedName]) {
                autoFillFromDictionary(this, dictionary[normalizedName], specialty, index);
            }
        });
    }

    /**
     * Rellena campos desde el diccionario
     */
    function autoFillFromDictionary(input, medData, specialty, index) {
        const container = input.closest('.section-grid') || input.closest('.form-group').parentElement;
        if (!container) return;

        // Rellenar indicación
        const indicacionInput = container.querySelector(`[name*="[indicacion]"]`);
        if (indicacionInput && medData.indicacion) {
            indicacionInput.value = medData.indicacion;
        }

        // Si hay vía seleccionada, actualizar dosis
        const viaSelect = container.querySelector(`[name*="[via]"]`);
        if (viaSelect && medData.dosis) {
            const via = viaSelect.value || 'IV';
            if (medData.dosis[via]) {
                const dosisInput = container.querySelector(`[name*="[dosis]"]`);
                if (dosisInput) {
                    dosisInput.value = medData.dosis[via];
                }
            }
        }
    }

    /**
     * Configura normalización a mayúsculas
     * Excepto en formularios de autenticación (.auth-form)
     */
    function setupNormalization() {
        // Helper: verificar si un elemento está dentro de un formulario de auth
        function isInsideAuthForm(element) {
            return element.closest('.auth-form') !== null;
        }

        // Normalizar inputs de texto (excepto en login/register)
        document.querySelectorAll('input[type="text"]').forEach(input => {
            if (isInsideAuthForm(input)) return; // ← excepción: no normalizar auth
            input.addEventListener('blur', function() {
                if (this.value) {
                    this.value = normalizeToUpper(this.value);
                }
            });
        });

        // Normalizar selects (excepto en login/register)
        document.querySelectorAll('select').forEach(select => {
            if (isInsideAuthForm(select)) return; // ← excepción: no normalizar auth
            select.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption && selectedOption.text) {
                    selectedOption.text = normalizeToUpper(selectedOption.text);
                }
            });
        });
    }

    /**
     * Configura manejadores de vía de administración
     */
    function setupViaHandlers() {
        document.querySelectorAll('.via-select').forEach(select => {
            select.addEventListener('change', function() {
                updateUnidadesForVia(this);
            });
            // Inicializar
            updateUnidadesForVia(select);
        });
    }

    /**
     * Actualiza unidades disponibles según vía
     */
    function updateUnidadesForVia(viaSelect) {
        const container = viaSelect.closest('.section-grid') || viaSelect.closest('.form-group').parentElement;
        if (!container) return;

        const via = viaSelect.value || 'IV';
        const unidadSelect = container.querySelector(`[name*="[unidad]"]`);
        
        if (!unidadSelect) return;

        // Obtener unidades según vía
        const viaData = MEDICATION_DICTIONARY_V2.vias[via];
        if (!viaData) return;

        const unidades = viaData.unidades;
        const currentValue = unidadSelect.value;

        // Generar opciones
        let html = '<option value="">SELECCIONAR...</option>';
        unidades.forEach(u => {
            const selected = u === currentValue ? ' selected' : '';
            html += `<option value="${u}"${selected}>${u}</option>`;
        });
        
        unidadSelect.innerHTML = html;
    }

    /**
     * Agrega una nueva fila de medicamento
     */
    function addMedicationRow(tableName) {
        const specialty = SPECIALTY_MAP[tableName];
        if (!specialty) return;

        counters[tableName] = (counters[tableName] || 0) + 1;
        const index = counters[tableName];

        // Crear nueva fila HTML
        const row = document.createElement('div');
        row.className = 'section-grid medication-row';
        row.style.cssText = 'grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border);';
        
        row.innerHTML = `
            <div class="form-group">
                <label>Medicamento</label>
                <input type="text" name="dynamic_${tableName}[${index}][medicamento]" 
                       placeholder="Ej: MIDAZOLAM" class="medication-input">
            </div>
            <div class="form-group">
                <label>Vía</label>
                <select name="dynamic_${tableName}[${index}][via]" class="via-select" data-table="${specialty}">
                    ${generarOpcionesVias()}
                </select>
            </div>
            <div class="form-group">
                <label>Unidad</label>
                <select name="dynamic_${tableName}[${index}][unidad]">
                    <option value="">SELECCIONAR...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Dosis</label>
                <input type="text" name="dynamic_${tableName}[${index}][dosis]" placeholder="Ej: 2-5">
            </div>
            <div class="form-group">
                <label>Frecuencia</label>
                <select name="dynamic_${tableName}[${index}][frecuencia]">
                    ${generarOpcionesFrecuencias()}
                </select>
            </div>
            <div class="form-group">
                <label>Fecha Inicio</label>
                <input type="date" name="dynamic_${tableName}[${index}][fecha_inicio]">
            </div>
            <div class="form-group">
                <label>Fecha Fin</label>
                <input type="date" name="dynamic_${tableName}[${index}][fecha_fin]">
            </div>
            <div class="form-group" style="grid-column: span 2;">
                <label>Indicación</label>
                <input type="text" name="dynamic_${tableName}[${index}][indicacion]" placeholder="Ej: SEDACION, CONTROL DE CRISIS">
            </div>
            <div class="form-group" style="display: flex; align-items: flex-end;">
                <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.medication-row').remove()">✕ Eliminar</button>
            </div>
        `;

        // Insertar antes del botón de agregar
        const container = document.querySelector(`[data-table="${tableName}"]`).closest('.dynamic-form-section');
        container.insertBefore(row, container.querySelector('.add-medication-btn'));

        // Configurar autocompletado
        const medInput = row.querySelector('.medication-input');
        if (medInput && MEDICATION_DICTIONARY_V2[specialty]) {
            setupAutocomplete(medInput, MEDICATION_DICTIONARY_V2[specialty], specialty, index);
        }

        // Configurar vía
        const viaSelect = row.querySelector('.via-select');
        if (viaSelect) {
            setupViaHandlers();
        }
    }

    // Exponer funciones globales
    window.initMedicationHandlers = initMedicationHandlers;
    window.addMedicationRow = addMedicationRow;
    window.updateUnidadesForVia = updateUnidadesForVia;

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMedicationHandlers);
    } else {
        initMedicationHandlers();
    }
})();
