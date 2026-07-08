/**
 * Diccionario de Medicamentos por Especialidad
 * Autocompletado inteligente con datos predefinidos
 */

const MEDICATION_DICTIONARY = {
    // Medicamentos Neurológicos
    neurologicos: {
        'Midazolam': { unidad: 'mg', dosis: '2-5', indicacion: 'Sedación' },
        'Propofol': { unidad: 'mg/kg/h', dosis: '5-50', indicacion: 'Sedación/Anestesia' },
        'Fentanilo': { unidad: 'mcg/h', dosis: '25-100', indicacion: 'Analgesia' },
        'Morfina': { unidad: 'mg', dosis: '2-10', indicacion: 'Dolor agudo' },
        'Dexmedetomidina': { unidad: 'mcg/kg/h', dosis: '0.2-0.7', indicacion: 'Sedación' },
        'Ketamina': { unidad: 'mg/kg/h', dosis: '0.1-0.5', indicacion: 'Analgesia/Sedación' },
        'Levetiracetam': { unidad: 'mg', dosis: '500-1500', indicacion: 'Antiepiléptico' },
        'Fenitoína': { unidad: 'mg', dosis: '100-300', indicacion: 'Crisis convulsivas' },
        'Valproato': { unidad: 'mg', dosis: '500-1500', indicacion: 'Antiepiléptico' },
        'Mannitol': { unidad: 'g', dosis: '0.25-1', indicacion: 'Edema cerebral' },
        'Furosemida': { unidad: 'mg', dosis: '20-40', indicacion: 'Edema cerebral/Hiperosmolar' },
        'Haloperidol': { unidad: 'mg', dosis: '2-10', indicacion: 'Delirium' },
        'Quetiapina': { unidad: 'mg', dosis: '25-200', indicacion: 'Delirium/PSI' },
        'Olanzapina': { unidad: 'mg', dosis: '2.5-10', indicacion: 'Delirium/Agitación' },
        'Lorazepam': { unidad: 'mg', dosis: '1-4', indicacion: 'Ansiedad/Convulsiones' },
        'Diazepam': { unidad: 'mg', dosis: '5-10', indicacion: 'Status epiléptico' }
    },

    // Medicamentos Hemodinámicos
    hemodinamicos: {
        'Noradrenalina': { unidad: 'mcg/min', dosis_max: '1.0', dosis_min: '0.05', indicacion: 'Choque séptico' },
        'Adrenalina': { unidad: 'mcg/min', dosis_max: '2.0', dosis_min: '0.1', indicacion: 'PCR/Choque anafiláctico' },
        'Dopamina': { unidad: 'mcg/kg/min', dosis_max: '20', dosis_min: '5', indicacion: 'Choque cardiogénico' },
        'Dobutamina': { unidad: 'mcg/kg/min', dosis_max: '20', dosis_min: '2.5', indicacion: 'Insuficiencia cardíaca' },
        'Vasopresina': { unidad: 'UI/min', dosis_max: '0.04', dosis_min: '0.01', indicacion: 'Choque distributivo' },
        'Terlipresina': { unidad: 'mg', dosis_max: '2', dosis_min: '1', indicacion: 'Sangrado variceal' },
        'Milrinona': { unidad: 'mcg/kg/min', dosis_max: '0.75', dosis_min: '0.125', indicacion: 'Insuficiencia cardíaca' },
        'Levosimendán': { unidad: 'mcg/kg/min', dosis_max: '0.2', dosis_min: '0.05', indicacion: 'Shock cardiogénico' },
        'Nitroprusiato': { unidad: 'mcg/kg/min', dosis_max: '10', dosis_min: '0.3', indicacion: 'Emergencia hipertensiva' },
        'Nitroglicerina': { unidad: 'mcg/min', dosis_max: '200', dosis_min: '5', indicacion: 'Angina/Edema agudo' },
        'Esmolol': { unidad: 'mcg/kg/min', dosis_max: '200', dosis_min: '50', indicacion: 'Taquicardia SVT' },
        'Labetalol': { unidad: 'mg', dosis_max: '300', dosis_min: '20', indicacion: 'Emergencia hipertensiva' },
        'Hidralazina': { unidad: 'mg', dosis_max: '40', dosis_min: '10', indicacion: 'Emergencia hipertensiva' },
        'Nicardipino': { unidad: 'mg/h', dosis_max: '15', dosis_min: '5', indicacion: 'Emergencia hipertensiva' },
        'Clonidina': { unidad: 'mcg/h', dosis_max: '900', dosis_min: '100', indicacion: 'Síndrome de abstinencia' }
    },

    // Medicamentos Nefrólogos
    nefro: {
        'Furosemida': { unidad: 'mg', dosis: '20-200', indicacion: 'Diuresis forzada/Edema' },
        'Bumetanida': { unidad: 'mg', dosis: '1-4', indicacion: 'Insuficiencia cardíaca' },
        'Torasemida': { unidad: 'mg', dosis: '5-20', indicacion: 'Edema/Hipertensión' },
        'Metolazona': { unidad: 'mg', dosis: '2.5-10', indicacion: 'Diurético de asa' },
        'Acetazolamida': { unidad: 'mg', dosis: '250-500', indicacion: 'Alcalosis metabólica' },
        'Hidroclorotiazida': { unidad: 'mg', dosis: '12.5-50', indicacion: 'Hipertensión/Edema' },
        'Eplerenona': { unidad: 'mg', dosis: '25-50', indicacion: 'Insuficiencia cardíaca' },
        'Espironolactona': { unidad: 'mg', dosis: '25-100', indicacion: 'Insuficiencia cardíaca/Ascitis' },
        'Clorthalidona': { unidad: 'mg', dosis: '12.5-25', indicacion: 'Hipertensión' },
        'Dopamina baja': { unidad: 'mcg/kg/min', dosis: '1-3', indicacion: 'Flujo renal' }
    },

    // Medicamentos Gastrointestinales
    gastro: {
        'Omeprazol': { unidad: 'mg', dosis: '20-40', indicacion: 'Protección gástrica/GERD' },
        'Esomeprazol': { unidad: 'mg', dosis: '20-40', indicacion: 'Síndrome de Zollinger-Ellison' },
        'Pantoprazol': { unidad: 'mg', dosis: '40-80', indicacion: 'Protección gástrica' },
        'Ranitidina': { unidad: 'mg', dosis: '50-150', indicacion: 'Bloqueo H2' },
        'Famotidina': { unidad: 'mg', dosis: '20-40', indicacion: 'Protección gástrica' },
        'Metoclopramida': { unidad: 'mg', dosis: '10', indicacion: 'Náuseas/Vómitos' },
        'Ondansetrón': { unidad: 'mg', dosis: '4-8', indicacion: 'Náuseas post-quimioterapia' },
        'Dexametasona': { unidad: 'mg', dosis: '4-8', indicacion: 'Náuseas refractarias' },
        'Haloperidol': { unidad: 'mg', dosis: '0.5-2', indicacion: 'Náuseas refractarias' },
        'Loperamida': { unidad: 'mg', dosis: '2-4', indicacion: 'Diarrea' },
        'Octreotida': { unidad: 'mcg', dosis: '50-100', indicacion: 'Sangrado digestivo' },
        'Sucralfato': { unidad: 'g', dosis: '1', indicacion: 'Úlcera gástrica' },
        'Lactulosa': { unidad: 'ml', dosis: '15-30', indicacion: 'Encefalopatía hepática' },
        'Rifaximina': { unidad: 'mg', dosis: '400', indicacion: 'Encefalopatía hepática' },
        'Neomicina': { unidad: 'mg', dosis: '500-1000', indicacion: 'Preparación intestinal' }
    },

    // Medicación Hematológica
    hematologica: {
        'Heparina no fraccionada': { unidad: 'UI/h', dosis: '1000-2000', indicacion: 'Profilaxis/Trombosis' },
        'Heparina de bajo peso molecular': { unidad: 'mg', dosis: '40-60', indicacion: 'Profilaxis anticoagulante' },
        'Enoxaparina': { unidad: 'mg', dosis: '40-60', indicacion: 'Profilaxis anticoagulante' },
        'Dalteparina': { unidad: 'UI', dosis: '2500-5000', indicacion: 'Profilaxis/TEP' },
        'Tinzaparina': { unidad: 'UI', dosis: '3500-4500', indicacion: 'Trombosis venosa profunda' },
        'Warfarina': { unidad: 'mg', dosis: '2-10', indicacion: 'Anticoagulación crónica' },
        'Rivaroxabán': { unidad: 'mg', dosis: '10-20', indicacion: 'Tromboembolia venosa' },
        'Apixabán': { unidad: 'mg', dosis: '2.5-5', indicacion: 'Prevención ACV' },
        'Dabigatrán': { unidad: 'mg', dosis: '75-150', indicacion: 'Tromboembolia' },
        'Fondaparinux': { unidad: 'mg', dosis: '2.5-10', indicacion: 'Síndrome coronario agudo' },
        'Argatroban': { unidad: 'mcg/kg/min', dosis: '2', indicacion: 'Trombosis con HIT' },
        'Bivalirudina': { unidad: 'mg/h', dosis: '0.75-1.75', indicacion: 'Intervención coronaria' },
        'Desmopresina': { unidad: 'mcg', dosis: '0.3', indicacion: 'Sangrado uremico' },
        'Ácido tranexámico': { unidad: 'g', dosis: '1', indicacion: 'Sangrado traumático/Quirúrgico' },
        'Vitamina K': { unidad: 'mg', dosis: '1-10', indicacion: 'Sangrado por warfarina' },
        'Protamina': { unidad: 'mg', dosis: '1-1.5', indicacion: 'Reversión heparina' },
        'Filgrastim': { unidad: 'mcg', dosis: '300-600', indicacion: 'Neutropenia' },
        'Epoetina alfa': { unidad: 'UI', dosis: '4000-10000', indicacion: 'Anemia' },
        'Factor VIIa recombinante': { unidad: 'mcg/kg', dosis: '90', indicacion: 'Sangrado masivo' },
        'Complejo protrombínico': { unidad: 'UI/kg', dosis: '25-50', indicacion: 'Sangrado anticoagulante' },
        'Fibrinógeno': { unidad: 'g', dosis: '2-4', indicacion: 'Hipofibrinogenemia' },
        'Crioprecipitados': { unidad: 'unidades', dosis: '6-10', indicacion: 'Deficiencia factor VIII' }
    }
};

/**
 * Inicializa autocompletado para todos los campos de medicamentos
 */
function initMedicationAutocomplete() {
    const specialtyMap = {
        'medicamentos_neurologicos': 'neurologicos',
        'medicamentos_hemodinamicos': 'hemodinamicos',
        'medicamentos_nefro': 'nefro',
        'medicamentos_gastro': 'gastro',
        'medicacion_hematologica': 'hematologica'
    };

    // Buscar todos los inputs de medicamentos
    document.querySelectorAll('input[name*="[medicamento]"]').forEach(input => {
        const name = input.name;
        let specialty = null;
        
        // Identificar la especialidad
        for (const [prefix, spec] of Object.entries(specialtyMap)) {
            if (name.includes(prefix)) {
                specialty = spec;
                break;
            }
        }

        if (!specialty) return;

        const dictionary = MEDICATION_DICTIONARY[specialty];
        if (!dictionary) return;

        // Crear contenedor del autocompletado
        setupAutocomplete(input, dictionary, specialty);
    });
}

/**
 * Configura el sistema de autocompletado
 */
function setupAutocomplete(input, dictionary, specialty) {
    // Crear datalist dinámico
    const datalistId = `meds-${specialty}-${Date.now()}`;
    let datalist = document.getElementById(datalistId);
    
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = datalistId;
        document.body.appendChild(datalist);
    }

    // Añadir opciones al datalist
    const medications = Object.keys(dictionary);
    datalist.innerHTML = medications.map(med => `<option value="${med}">`).join('');
    input.setAttribute('list', datalistId);

    // Evento al escribir
    input.addEventListener('input', function(e) {
        const value = e.target.value.trim();
        updateSuggestions(input, datalist, dictionary, value);
    });

    // Evento al seleccionar
    input.addEventListener('change', function(e) {
        const value = e.target.value.trim();
        if (dictionary[value]) {
            autoFillFields(input, dictionary[value], specialty);
        }
    });

    // Autocompletado con Tab
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const value = input.value.trim().toLowerCase();
            const match = findBestMatch(value, Object.keys(dictionary));
            if (match) {
                e.preventDefault();
                input.value = match;
                autoFillFields(input, dictionary[match], specialty);
            }
        }
    });
}

/**
 * Actualiza las sugerencias del datalist
 */
function updateSuggestions(input, datalist, dictionary, value) {
    if (value.length < 2) return;

    const medications = Object.keys(dictionary);
    const matches = medications.filter(med => 
        med.toLowerCase().includes(value.toLowerCase())
    ).slice(0, 10); // Máximo 10 sugerencias

    datalist.innerHTML = matches.map(med => `<option value="${med}">`).join('');
}

/**
 * Encuentra la mejor coincidencia
 */
function findBestMatch(value, options) {
    if (!value) return null;
    
    const lowerValue = value.toLowerCase();
    return options.find(opt => opt.toLowerCase().startsWith(lowerValue)) ||
           options.find(opt => opt.toLowerCase().includes(lowerValue));
}

/**
 * Rellena automáticamente los campos relacionados
 */
function autoFillFields(input, data, specialty) {
    // Obtener el índice del input actual
    const nameMatch = input.name.match(/\[(\d+)\]/);
    if (!nameMatch) return;
    
    const index = nameMatch[1];
    const baseName = input.name.replace(/\[medicamento\]$/, '');

    // Mapeo de campos según especialidad
    const fieldMap = {
        'neurologicos': ['unidad', 'dosis', 'indicacion'],
        'hemodinamicos': ['unidad', 'dosis_max', 'dosis_min', 'indicacion'],
        'nefro': ['unidad', 'dosis', 'indicacion'],
        'gastro': ['unidad', 'dosis', 'indicacion'],
        'hematologica': ['unidad', 'dosis', 'indicacion']
    };

    const fields = fieldMap[specialty] || [];
    
    fields.forEach(field => {
        const targetInput = document.querySelector(`input[name="${baseName}[${index}][${field}]"], select[name="${baseName}[${index}][${field}]"]`);
        if (targetInput && data[field]) {
            targetInput.value = data[field];
            // Animación de resaltado
            targetInput.style.backgroundColor = 'rgba(255, 107, 53, 0.2)';
            setTimeout(() => {
                targetInput.style.backgroundColor = '';
            }, 800);
        }
    });

    // Fecha de inicio por defecto = hoy
    const fechaInicio = document.querySelector(`input[name="${baseName}[${index}][fecha_inicio]"]`);
    if (fechaInicio && !fechaInicio.value) {
        fechaInicio.value = new Date().toISOString().split('T')[0];
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initMedicationAutocomplete);

// También exponer función global para recarga dinámica
window.initMedicationAutocomplete = initMedicationAutocomplete;
