/**
 * SINAPSID - Sistema de Autocomplete para Medicamentos
 * Maneja el diccionario de medicamentos con autocomplete, sugerencias de unidades y tabla dinámica
 */

// Almacenar datos de medicamentos cargados
let medicationsData = null;

/**
 * Cargar datos de medicamentos desde el JSON
 */
async function loadMedicationsData() {
    if (medicationsData) return medicationsData;
    
    try {
        const response = await fetch('/static/data/medications.json');
        if (!response.ok) throw new Error('Error cargando medicamentos');
        medicationsData = await response.json();
        return medicationsData;
    } catch (error) {
        console.error('Error cargando medications.json:', error);
        return null;
    }
}

/**
 * Obtener la lista de medicamentos por categoría
 */
function getMedicationsByCategory(category) {
    if (!medicationsData || !medicationsData[category]) return [];
    return medicationsData[category].medicamentos || [];
}

/**
 * Buscar medicamentos por nombre (autocomplete)
 * @param {string} query - Texto de búsqueda (mínimo 2 caracteres)
 * @param {string} category - Categoría de medicamentos
 * @returns {Array} Lista de medicamentos coincidentes
 */
function searchMedications(query, category) {
    if (!query || query.length < 2) return [];
    
    const medications = getMedicationsByCategory(category);
    const lowerQuery = query.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    
    return medications.filter(med => {
        const normalizedName = med.nombre.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        return normalizedName.includes(lowerQuery);
    }).slice(0, 10); // Máximo 10 resultados
}

/**
 * Crear el datalist para autocomplete de medicamentos
 * @param {string} category - Categoría de medicamentos
 */
async function createMedicationsDatalist(category) {
    await loadMedicationsData();
    
    const datalistId = `datalist-medicamentos-${category}`;
    let datalist = document.getElementById(datalistId);
    
    // Crear datalist si no existe
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = datalistId;
        document.body.appendChild(datalist);
    }
    
    // Limpiar opciones existentes
    datalist.innerHTML = '';
    
    // Agregar opciones
    const medications = getMedicationsByCategory(category);
    medications.forEach(med => {
        const option = document.createElement('option');
        option.value = med.nombre;
        option.dataset.unidades = JSON.stringify(med.unidades_sugeridas);
        option.dataset.dosis = med.dosis_tipicas;
        datalist.appendChild(option);
    });
    
    return datalistId;
}

/**
 * Configurar autocomplete en un input de medicamento
 * @param {HTMLInputElement} input - Input del medicamento
 * @param {string} category - Categoría (hemodinamicos, neurologicos, etc.)
 * @param {HTMLInputElement} unitInput - Input de unidad (opcional)
 */
async function setupMedicationAutocomplete(input, category, unitInput = null) {
    await loadMedicationsData();
    
    // Crear datalist
    const datalistId = await createMedicationsDatalist(category);
    input.setAttribute('list', datalistId);
    
    // Crear contenedor para sugerencias
    const wrapper = document.createElement('div');
    wrapper.className = 'medication-autocomplete-wrapper';
    wrapper.style.position = 'relative';
    wrapper.style.display = 'inline-block';
    wrapper.style.width = '100%';
    
    // Mover input al wrapper
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    
    // Crear lista de sugerencias
    const suggestionsList = document.createElement('ul');
    suggestionsList.className = 'medication-suggestions';
    suggestionsList.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-top: none;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
        list-style: none;
        margin: 0;
        padding: 0;
        display: none;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    `;
    wrapper.appendChild(suggestionsList);
    
    // Manejar input para mostrar sugerencias
    let currentFocus = -1;
    
    input.addEventListener('input', function(e) {
        const val = this.value;
        suggestionsList.innerHTML = '';
        currentFocus = -1;
        
        if (val.length < 2) {
            suggestionsList.style.display = 'none';
            return;
        }
        
        const matches = searchMedications(val, category);
        
        if (matches.length === 0) {
            suggestionsList.style.display = 'none';
            return;
        }
        
        matches.forEach((med, index) => {
            const li = document.createElement('li');
            li.style.cssText = `
                padding: 8px 12px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            `;
            li.innerHTML = `
                <strong>${med.nombre}</strong>
                <small style="display: block; color: #666; font-size: 11px;">${med.dosis_tipicas}</small>
            `;
            
            li.addEventListener('click', function() {
                input.value = med.nombre;
                suggestionsList.style.display = 'none';
                
                // Autocompletar unidades si se proporcionó el input
                if (unitInput && med.unidades_sugeridas && med.unidades_sugeridas.length > 0) {
                    unitInput.value = med.unidades_sugeridas[0];
                    // Mostrar tooltip con otras unidades disponibles
                    unitInput.title = `Unidades disponibles: ${med.unidades_sugeridas.join(', ')}`;
                }
                
                // Trigger change event
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
            
            li.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f0f0f0';
            });
            
            li.addEventListener('mouseleave', function() {
                this.style.backgroundColor = 'white';
            });
            
            suggestionsList.appendChild(li);
        });
        
        suggestionsList.style.display = 'block';
    });
    
    // Navegación con teclado
    input.addEventListener('keydown', function(e) {
        const items = suggestionsList.getElementsByTagName('li');
        
        if (e.key === 'ArrowDown') {
            currentFocus++;
            addActive(items);
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            currentFocus--;
            addActive(items);
            e.preventDefault();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentFocus > -1) {
                items[currentFocus].click();
            }
        } else if (e.key === 'Escape') {
            suggestionsList.style.display = 'none';
        }
    });
    
    function addActive(items) {
        if (!items) return;
        removeActive(items);
        if (currentFocus >= items.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = items.length - 1;
        items[currentFocus].style.backgroundColor = '#e0e0e0';
    }
    
    function removeActive(items) {
        for (let i = 0; i < items.length; i++) {
            items[i].style.backgroundColor = 'white';
        }
    }
    
    // Cerrar al hacer click fuera
    document.addEventListener('click', function(e) {
        if (e.target !== input && e.target !== suggestionsList) {
            suggestionsList.style.display = 'none';
        }
    });
}

/**
 * Crear datalist para unidades de una categoría
 * @param {string} category - Categoría de medicamentos
 */
async function createUnitsDatalist(category) {
    await loadMedicationsData();
    
    const datalistId = `datalist-unidades-${category}`;
    let datalist = document.getElementById(datalistId);
    
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = datalistId;
        document.body.appendChild(datalist);
    }
    
    datalist.innerHTML = '';
    
    if (medicationsData[category] && medicationsData[category].unidades_comunes) {
        medicationsData[category].unidades_comunes.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit;
            datalist.appendChild(option);
        });
    }
    
    return datalistId;
}

/**
 * Nueva plantilla de fila para medicamentos con autocomplete
 */
const medTemplatesEnhanced = {
    neurologicos: `
        <td><input type="text" name="neurologicos_medicamento[]" class="med-input" placeholder="Escriba para buscar..." autocomplete="off"></td>
        <td><input type="text" name="neurologicos_unidad[]" class="unit-input" placeholder="Unidad" list="datalist-unidades-neurologicos"></td>
        <td><input type="text" name="neurologicos_dosis[]" placeholder="Dosis"></td>
        <td><input type="date" name="neurologicos_fecha_inicio[]"></td>
        <td><input type="date" name="neurologicos_fecha_fin[]"></td>
        <td><input type="text" name="neurologicos_indicacion[]" placeholder="Indicación"></td>
    `,
    hemodinamicos: `
        <td><input type="text" name="hemodinamicos_medicamento[]" class="med-input" placeholder="Escriba para buscar..." autocomplete="off"></td>
        <td><input type="text" name="hemodinamicos_unidad[]" class="unit-input" placeholder="mcg/kg/min" list="datalist-unidades-hemodinamicos"></td>
        <td><input type="text" name="hemodinamicos_dosis_max[]" placeholder="Máx"></td>
        <td><input type="text" name="hemodinamicos_dosis_min[]" placeholder="Mín"></td>
        <td><input type="date" name="hemodinamicos_fecha_inicio[]"></td>
        <td><input type="date" name="hemodinamicos_fecha_fin[]"></td>
        <td><input type="text" name="hemodinamicos_indicacion[]" placeholder="Indicación"></td>
    `,
    nefro: `
        <td><input type="text" name="nefro_medicamento[]" class="med-input" placeholder="Escriba para buscar..." autocomplete="off"></td>
        <td><input type="text" name="nefro_unidad[]" class="unit-input" placeholder="mg" list="datalist-unidades-nefro"></td>
        <td><input type="text" name="nefro_dosis[]" placeholder="Dosis"></td>
        <td><input type="date" name="nefro_fecha_inicio[]"></td>
        <td><input type="date" name="nefro_fecha_fin[]"></td>
    `,
    gastro: `
        <td><input type="text" name="gastro_medicamento[]" class="med-input" placeholder="Escriba para buscar..." autocomplete="off"></td>
        <td><input type="text" name="gastro_unidad[]" class="unit-input" placeholder="mg" list="datalist-unidades-gastro"></td>
        <td><input type="text" name="gastro_dosis[]" placeholder="Dosis"></td>
        <td><input type="date" name="gastro_fecha_inicio[]"></td>
        <td><input type="date" name="gastro_fecha_fin[]"></td>
    `,
    hematologica: `
        <td><input type="text" name="hematologica_medicamento[]" class="med-input" placeholder="Escriba para buscar..." autocomplete="off"></td>
        <td><input type="text" name="hematologica_dosis[]" placeholder="Dosis"></td>
        <td><input type="text" name="hematologica_unidad[]" class="unit-input" placeholder="Unidad" list="datalist-unidades-hematologicos"></td>
        <td><input type="date" name="hematologica_fecha_inicio[]"></td>
        <td><input type="date" name="hematologica_fecha_fin[]"></td>
        <td><input type="text" name="hematologica_indicacion[]" placeholder="Indicación"></td>
    `
};

/**
 * Agregar fila de medicamento mejorada con autocomplete
 * @param {string} category - Categoría de medicamentos
 */
async function addMedRowEnhanced(category) {
    const tableId = 'table-medicamentos-' + category;
    const tbody = document.querySelector('#' + tableId + ' tbody');
    
    if (!tbody) {
        console.error('No se encontró tbody para:', tableId);
        return;
    }
    
    const row = document.createElement('tr');
    row.innerHTML = medTemplatesEnhanced[category] + `
        <td><button type="button" class="btn btn-danger" onclick="this.closest('tr').remove()">🗑️</button></td>
    `;
    
    tbody.appendChild(row);
    
    // Inicializar autocomplete en el input de medicamento
    const medInput = row.querySelector('.med-input');
    const unitInput = row.querySelector('.unit-input');
    
    if (medInput) {
        await setupMedicationAutocomplete(medInput, category, unitInput);
    }
}

/**
 * Inicializar todos los autocompletes y datalists en la página
 */
async function initializeMedicationSystem() {
    await loadMedicationsData();
    
    const categories = ['neurologicos', 'hemodinamicos', 'nefro', 'gastro', 'hematologica'];
    
    // Crear datalists de unidades para todas las categorías
    for (const category of categories) {
        await createUnitsDatalist(category);
    }
    
    // Reemplazar función addMedRow global
    window.addMedRow = addMedRowEnhanced;
    
    // Inicializar autocompletes en filas existentes
    categories.forEach(category => {
        const table = document.getElementById('table-medicamentos-' + category);
        if (table) {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const medInput = row.querySelector('input[name*="medicamento"]');
                const unitInput = row.querySelector('input[name*="unidad"]');
                if (medInput && !medInput.dataset.autocompleteInitialized) {
                    setupMedicationAutocomplete(medInput, category, unitInput);
                    medInput.dataset.autocompleteInitialized = 'true';
                }
            });
        }
    });
    
    // Agregar filas iniciales si está en modo 'new'
    const mode = document.querySelector('form')?.dataset?.mode || 'new';
    if (mode === 'new' && !window.medicationsInitialized) {
        // Verificar si ya hay filas
        categories.forEach(category => {
            const table = document.getElementById('table-medicamentos-' + category);
            if (table) {
                const existingRows = table.querySelectorAll('tbody tr');
                if (existingRows.length === 0) {
                    addMedRowEnhanced(category);
                }
            }
        });
        window.medicationsInitialized = true;
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initializeMedicationSystem);

// Exportar funciones para uso global
window.medicationsSystem = {
    loadMedicationsData,
    searchMedications,
    setupMedicationAutocomplete,
    addMedRowEnhanced,
    initializeMedicationSystem
};