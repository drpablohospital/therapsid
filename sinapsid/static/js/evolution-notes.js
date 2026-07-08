/**
 * SINAPSID - Sistema Unificado de Generación y Guardado de Notas Médicas
 * Versión 3.1 - Solo activo en evolution_form.html
 */

(function() {
    'use strict';
    
    // Verificar que estamos en la página correcta
    if (!document.getElementById('btnGenerarNota') || !document.getElementById('tipoNotaSelect')) {
        console.log('[NOTE-SYSTEM] No estamos en evolution_form.html - omitiendo inicialización');
        return;
    }
    
    console.log('[NOTE-SYSTEM] Sistema unificado de notas v3.1 cargado');
    
    // Estado global
    let currentNoteData = null;
    let isGenerating = false;
    
    /**
     * Inicialización principal
     */
    function initNoteSystem() {
        console.log('[NOTE-SYSTEM] Inicializando...');
        
        const btnGenerar = document.getElementById('btnGenerarNota');
        const tipoSelect = document.getElementById('tipoNotaSelect');
        
        if (!btnGenerar) {
            console.warn('[NOTE-SYSTEM] Botón generar no encontrado');
            return;
        }
        
        // Obtener patient_id del atributo data
        const patientId = btnGenerar.dataset.patientId;
        if (!patientId) {
            console.error('[NOTE-SYSTEM] No se encontró patient-id');
            return;
        }
        
        // Limpiar cualquier onclick previo y agregar event listener limpio
        btnGenerar.removeAttribute('onclick');
        btnGenerar.addEventListener('click', handleGenerateClick);
        
        // Verificar tipo seleccionado
        if (tipoSelect) {
            tipoSelect.addEventListener('change', function() {
                console.log('[NOTE-SYSTEM] Tipo seleccionado:', this.value);
            });
        }
        
        console.log('[NOTE-SYSTEM] Inicialización completa. Patient ID:', patientId);
    }
    
    /**
     * Manejador del clic en "Generar Nota"
     */
    async function handleGenerateClick(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (isGenerating) {
            console.log('[NOTE-SYSTEM] Ya se está generando, ignorando clic');
            return;
        }
        
        const btnGenerar = document.getElementById('btnGenerarNota');
        const tipoSelect = document.getElementById('tipoNotaSelect');
        const previewContainer = document.getElementById('previewContainer');
        const notaGenerada = document.getElementById('notaGenerada');
        
        const patientId = btnGenerar.dataset.patientId;
        
        // Validar tipo de nota
        if (!tipoSelect || !tipoSelect.value) {
            alert('⚠️ Por favor selecciona un tipo de nota');
            tipoSelect.focus();
            return;
        }
        
        // Mapear valor del select a template_id del backend
        const templateMap = {
            'ingreso': 'nota_ingreso_uci',
            'psoap': 'nota_evolucion_psoap',
            'egreso': 'nota_egreso',
            'simple': 'nota_medica_simple'
        };
        
        const templateId = templateMap[tipoSelect.value];
        if (!templateId) {
            alert('⚠️ Tipo de nota no válido');
            return;
        }
        
        // Estado de carga
        isGenerating = true;
        const originalText = btnGenerar.innerHTML;
        btnGenerar.disabled = true;
        btnGenerar.innerHTML = '⏳ Generando nota...';
        
        try {
            // Recolectar datos del formulario
            const formData = collectFormData();
            console.log('[NOTE-SYSTEM] Datos recolectados:', Object.keys(formData).length, 'campos');
            
            // Llamar API de generación
            console.log('[NOTE-SYSTEM] Llamando /api/generate-note...');
            const response = await fetch('/api/generate-note', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    patient_id: parseInt(patientId),
                    template_id: templateId,
                    form_data: formData
                })
            });
            
            console.log('[NOTE-SYSTEM] Response status:', response.status);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('[NOTE-SYSTEM] Resultado:', result.success ? 'OK' : 'ERROR');
            
            if (!result.success) {
                throw new Error(result.error || 'Error desconocido del servidor');
            }
            
            // Guardar datos para uso posterior
            currentNoteData = {
                patientId: parseInt(patientId),
                templateType: tipoSelect.value,
                templateTitle: result.template_title || 'Nota Clínica',
                content: result.note
            };
            
            // Mostrar resultado
            notaGenerada.value = result.note;
            previewContainer.style.display = 'block';
            previewContainer.scrollIntoView({ behavior: 'smooth' });
            
            console.log('[NOTE-SYSTEM] Nota generada y mostrada exitosamente');
            
        } catch (error) {
            console.error('[NOTE-SYSTEM] Error:', error);
            alert('❌ Error al generar nota:\n' + error.message);
        } finally {
            isGenerating = false;
            btnGenerar.disabled = false;
            btnGenerar.innerHTML = originalText;
        }
    }
    
    /**
     * Recolecta todos los datos del formulario de evolución
     */
    function collectFormData() {
        const data = {};
        
        // Campos principales con sus IDs
        const campoMap = {
            'fecha': 'evoFecha',
            'hora': 'evoHora',
            'fc': 'evoFc',
            'fr': 'evoFr',
            'tas': 'evoTas',
            'tad': 'evoTad',
            'tam': 'evoTam',
            'temperatura': 'evoTemp',
            'spo2': 'evoSpo2',
            'fio2': 'evoFio2',
            'pafi': 'evoPafi',
            'glasgow': 'evoGlasgow',
            'rass': 'evoRass',
            'modo_ventilatorio': 'evoModoVent',
            'vt_psinp': 'evoVt',
            'peep': 'evoPeep',
            'ppico': 'evoPpico',
            'pplat': 'evoPplat',
            'glucosa': 'evoGlucosa',
            'sodio': null, // Sin ID específico, buscar por name
            'potasio': null,
            'creatinina': 'evoCreatinina',
            'urea': null,
            'hemoglobina': 'evoHb',
            'leucocitos': 'evoLeuco',
            'plaquetas': 'evoPlaq',
            'pcr': 'evoPcr',
            'ingresos': 'evoIngresos',
            'egresos': 'evoEgresos',
            'diuresis': 'evoDiuresis',
            'drenajes': 'evoDrenajes',
            'balance': 'evoBalance',
            'nota': 'evoNota',
            'plan': 'evoPlan'
        };
        
        for (const [campo, idElemento] of Object.entries(campoMap)) {
            let el = null;
            
            if (idElemento) {
                el = document.getElementById(idElemento);
            }
            
            // Si no se encontró por ID, buscar por name
            if (!el) {
                el = document.querySelector(`[name="${campo}"]`);
            }
            
            if (el && el.value !== undefined) {
                const val = el.value.trim();
                if (val !== '') {
                    data[campo] = val;
                }
            }
        }
        
        return data;
    }
    
    // ═══════════════════════════════════════════════════════════════
    // FUNCIONES GLOBALES (llamadas desde onclick en HTML)
    // ═══════════════════════════════════════════════════════════════
    
    /**
     * Copiar nota generada al portapapeles
     */
    window.copiarNotaGenerada = function() {
        const notaText = document.getElementById('notaGenerada');
        if (!notaText || !notaText.value.trim()) {
            alert('⚠️ No hay nota para copiar');
            return;
        }
        
        notaText.select();
        notaText.setSelectionRange(0, 99999); // Para móviles
        
        try {
            navigator.clipboard.writeText(notaText.value).then(() => {
                showButtonFeedback(event.target, '✅ Copiado!');
            }).catch(() => {
                // Fallback
                document.execCommand('copy');
                showButtonFeedback(event.target, '✅ Copiado!');
            });
        } catch (e) {
            document.execCommand('copy');
            showButtonFeedback(event.target, '✅ Copiado!');
        }
    };
    
    /**
     * Insertar nota generada en el campo de evolución
     */
    window.ponerNotaEnEvolucion = function() {
        const notaText = document.getElementById('notaGenerada');
        const evoNota = document.getElementById('evoNota');
        
        if (!notaText || !notaText.value.trim()) {
            alert('⚠️ No hay nota generada');
            return;
        }
        
        if (!evoNota) {
            alert('❌ No se encontró el campo de nota de evolución');
            return;
        }
        
        // Confirmar si ya hay contenido
        if (evoNota.value.trim() && !confirm('¿Reemplazar la nota de evolución actual con la nota generada?')) {
            return;
        }
        
        evoNota.value = notaText.value.trim();
        evoNota.scrollIntoView({ behavior: 'smooth' });
        
        // Feedback visual
        const originalBg = evoNota.style.backgroundColor;
        evoNota.style.backgroundColor = 'rgba(74, 222, 128, 0.2)';
        setTimeout(() => {
            evoNota.style.backgroundColor = originalBg;
        }, 1000);
        
        console.log('[NOTE-SYSTEM] Nota insertada en evolución');
    };
    
    /**
     * Guardar nota generada en la base de datos
     */
    window.guardarNotaGenerada = async function() {
        const notaText = document.getElementById('notaGenerada');
        
        if (!notaText || !notaText.value.trim()) {
            alert('⚠️ No hay nota para guardar');
            return;
        }
        
        if (!currentNoteData) {
            alert('❌ Error: No hay datos de la nota. Genera una nota primero.');
            return;
        }
        
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '⏳ Guardando...';
        
        try {
            console.log('[NOTE-SYSTEM] Guardando nota...');
            
            const response = await fetch('/api/save-note', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    patient_id: currentNoteData.patientId,
                    template_type: currentNoteData.templateType,
                    title: currentNoteData.templateTitle,
                    content: notaText.value.trim()
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Error al guardar');
            }
            
            showButtonFeedback(btn, '✅ Guardada!');
            console.log('[NOTE-SYSTEM] Nota guardada. ID:', result.note_id);
            
        } catch (error) {
            console.error('[NOTE-SYSTEM] Error guardando:', error);
            alert('❌ Error al guardar nota:\n' + error.message);
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    };
    
    // ═══════════════════════════════════════════════════════════════
    // UTILIDADES
    // ═══════════════════════════════════════════════════════════════
    
    /**
     * Feedback visual en botón
     */
    function showButtonFeedback(btn, text) {
        if (!btn) return;
        const original = btn.innerHTML;
        btn.innerHTML = text;
        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        }, 2000);
    }
    
    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNoteSystem);
    } else {
        initNoteSystem();
    }
    
})();
