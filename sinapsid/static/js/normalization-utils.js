/**
 * Utilidades de Normalización
 * Convierte todo a MAYÚSCULAS sin acentos
 */

const NORMALIZATION_MAP = {
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
    'ñ': 'N', 'Ñ': 'N',
    'ü': 'u', 'Ü': 'U'
};

/**
 * Convierte texto a mayúsculas sin acentos
 * @param {string} text - Texto a normalizar
 * @returns {string} - Texto en mayúsculas sin acentos
 */
function normalizeToUpper(text) {
    if (!text || typeof text !== 'string') return '';
    
    // Primero quitar acentos
    let normalized = text.split('').map(char => NORMALIZATION_MAP[char] || char).join('');
    
    // Luego convertir a mayúsculas
    return normalized.toUpperCase().trim();
}

/**
 * Vías de administración válidas
 */
const VIAS_ADMINISTRACION = {
    'BIC': { label: 'BIC (Bolo Intermitente Continuo)', unidades: ['MG/KG/D', 'MG/KG/H', 'MCG/KG/MIN', 'DU'] },
    'IV': { label: 'IV (Intravenosa)', unidades: ['MG', 'G', 'UI', 'MCG', 'ML', 'MG/KG', 'UI/KG'] },
    'SC': { label: 'SC (Subcutánea)', unidades: ['MG', 'UI', 'MCG', 'ML'] },
    'SNG': { label: 'SNG (Sonda Nasogástrica)', unidades: ['MG', 'G', 'ML', 'UI'] },
    'ORAL': { label: 'ORAL', unidades: ['MG', 'G', 'ML', 'UI', 'MG/KG'] },
    'OTRA': { label: 'OTRA', unidades: ['MG', 'G', 'UI', 'MCG', 'ML', 'UNIDADES', 'AMPOLLAS'] }
};

/**
 * Frecuencias de administración
 */
const FRECUENCIAS = [
    { value: '1D', label: '1D (CADA 24 HORAS)' },
    { value: '2D', label: '2D (CADA 12 HORAS)' },
    { value: '3D', label: '3D (CADA 8 HORAS)' },
    { value: '4D', label: '4D (CADA 6 HORAS)' },
    { value: '6D', label: '6D (CADA 4 HORAS)' },
    { value: 'CONTINUO', label: 'CONTINUO (INFUSIÓN)' },
    { value: 'PRN', label: 'PRN (SEGÚN NECESIDAD)' },
    { value: 'UNICA', label: 'DOSIS ÚNICA' }
];

/**
 * Obtiene unidades según vía de administración
 * @param {string} via - Código de vía (BIC, IV, SC, SNG, ORAL, OTRA)
 * @returns {Array} - Lista de unidades permitidas
 */
function getUnidadesPorVia(via) {
    const viaUpper = normalizeToUpper(via);
    const viaData = VIAS_ADMINISTRACION[viaUpper];
    return viaData ? viaData.unidades : VIAS_ADMINISTRACION['OTRA'].unidades;
}

/**
 * Obtiene label de vía de administración
 * @param {string} via - Código de vía
 * @returns {string} - Label descriptivo
 */
function getViaLabel(via) {
    const viaUpper = normalizeToUpper(via);
    const viaData = VIAS_ADMINISTRACION[viaUpper];
    return viaData ? viaData.label : viaUpper;
}

/**
 * Genera HTML de opciones para select de vías
 * @returns {string} - HTML de opciones
 */
function generarOpcionesVias() {
    return Object.entries(VIAS_ADMINISTRACION)
        .map(([key, data]) => `<option value="${key}">${data.label}</option>`)
        .join('');
}

/**
 * Genera HTML de opciones para select de frecuencias
 * @returns {string} - HTML de opciones
 */
function generarOpcionesFrecuencias() {
    return FRECUENCIAS
        .map(f => `<option value="${f.value}">${f.label}</option>`)
        .join('');
}

/**
 * Genera HTML de opciones para select de unidades según vía
 * @param {string} via - Código de vía
 * @returns {string} - HTML de opciones
 */
function generarOpcionesUnidades(via) {
    const unidades = getUnidadesPorVia(via);
    return unidades
        .map(u => `<option value="${u}">${u}</option>`)
        .join('');
}

/**
 * Normaliza un objeto completo (como datos de medicamento)
 * @param {Object} obj - Objeto a normalizar
 * @returns {Object} - Objeto normalizado
 */
function normalizeObject(obj) {
    if (!obj || typeof obj !== 'object') return obj;
    
    const normalized = {};
    for (const [key, value] of Object.entries(obj)) {
        const normalizedKey = normalizeToUpper(key);
        const normalizedValue = typeof value === 'string' ? normalizeToUpper(value) : value;
        normalized[normalizedKey] = normalizedValue;
    }
    return normalized;
}

/**
 * Normaliza array de objetos
 * @param {Array} arr - Array a normalizar
 * @returns {Array} - Array normalizado
 */
function normalizeArray(arr) {
    if (!Array.isArray(arr)) return arr;
    return arr.map(item => {
        if (typeof item === 'string') return normalizeToUpper(item);
        if (typeof item === 'object') return normalizeObject(item);
        return item;
    });
}

// Exportar para uso global
window.normalizeToUpper = normalizeToUpper;
window.VIAS_ADMINISTRACION = VIAS_ADMINISTRACION;
window.FRECUENCIAS = FRECUENCIAS;
window.getUnidadesPorVia = getUnidadesPorVia;
window.getViaLabel = getViaLabel;
window.generarOpcionesVias = generarOpcionesVias;
window.generarOpcionesFrecuencias = generarOpcionesFrecuencias;
window.generarOpcionesUnidades = generarOpcionesUnidades;
window.normalizeObject = normalizeObject;
window.normalizeArray = normalizeArray;