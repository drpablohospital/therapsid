"""
SINAPSID DMA - Sistema de Gestión de Pacientes UCI
==================================================
Flask Application - PostgreSQL Version - Puerto 5001
"""

import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, make_response
import json
from datetime import datetime, date
import os
import sys
import re

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sinapsid')

# Asegurar que modules esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from modules.calculations import calculate_computed_fields, calculate_all_scores
from psoap_dump import generar_nota_psoap_dump
from nota_egreso import generar_nota_egreso
from modules.database import (
    get_patient, get_all_patients, insert_patient, update_patient,
    delete_patient, discharge_patient, check_expediente_exists,
    get_dynamic_items, save_dynamic_tables_from_dict,
    create_evolution, get_evolutions, get_evolution, update_evolution, delete_evolution,
    get_clinical_notes, create_clinical_note, get_clinical_note,
    clear_patient_dynamic_tables, get_all_dynamic_tables,
    get_db_cursor
)
from modules.clinical_notes import note_generator
from modules.trend_charts import (
    generate_trend_chart, generate_vitals_chart,
    generate_liquids_chart, generate_labs_chart
)
from modules.library import get_all_articles, get_article, search_articles, get_library_stats, get_featured_article
from modules.auth import (
    login_required, require_role, authenticate_user, create_session,
    invalidate_session, save_beta_application, get_public_stats, create_user
)
from modules.privacy import mask_patient_data, get_user_institution
from modules.uci_note_bridge import generar_nota_ingreso_uci, disponible as uci_note_disponible
from modules.validation import validate_evolution_data

# Importar rutas de administración
from modules.admin_routes import register_admin_routes


# Importar módulo de análisis clínicos avanzados
from modules.clinical_analytics import (
    calculate_advanced_metrics, save_analytics, get_analytics
)
import json
import re
from datetime import datetime, date
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ProxyFix para Cloudflare (terminación SSL)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Registrar rutas de administración
register_admin_routes(app)
# Registrar dashboard de UCI
from modules.dashboard_api import dashboard_bp
app.register_blueprint(dashboard_bp)

print("🦞 Sinapsid DMA iniciado - Puerto 5001")

# Markdown filter for templates
@app.template_filter('markdown')
def markdown_filter(text):
    """Convierte markdown básico a HTML."""
    if not text:
        return ""
    
    # Headers
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Bold and italic
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Links [text](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # Code inline
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Lists
    # Convert bullet list items
    lines = text.split('\n')
    result = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            content = stripped[2:]
            result.append(f'<li>{content}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    
    if in_list:
        result.append('</ul>')
    
    text = '\n'.join(result)
    
    # Blockquotes
    lines = text.split('\n')
    result = []
    in_quote = False
    
    for line in lines:
        if line.strip().startswith('> '):
            if not in_quote:
                result.append('<blockquote>')
                in_quote = True
            result.append(line.strip()[2:])
        else:
            if in_quote:
                result.append('</blockquote>')
                in_quote = False
            result.append(line)
    
    if in_quote:
        result.append('</blockquote>')
    
    text = '\n'.join(result)
    
    # Horizontal rule
    text = re.sub(r'^---+$', r'<hr>', text, flags=re.MULTILINE)
    
    # Line breaks
    text = text.replace('\n\n', '</p><p>')
    text = text.replace('\n', '<br>')
    
    # Wrap in paragraphs if not already wrapped
    if not text.startswith('<'):
        text = f'<p>{text}</p>'
    
    return text

# ============================================================================
# FIELD DEFINITIONS - 187 campos del clinical_manager_audit.md
# ============================================================================

PATIENT_FIELDS = {
    # Contextual Data
    'nombre_completo': {'type': 'text', 'required': True},
    'fecha_nacimiento': {'type': 'date'},
    'edad': {'type': 'integer'},
    'sexo': {'type': 'text'},
    'procedencia': {'type': 'text'},
    'servicio_tratante': {'type': 'text'},
    'fecha_ingreso_hosp': {'type': 'date'},
    'fecha_ingreso': {'type': 'date'},
    'dias_estancia': {'type': 'integer'},
    'cama': {'type': 'text'},
    'expediente': {'type': 'text', 'unique': True},
    'curp': {'type': 'text'},
    'episodio': {'type': 'text'},
    
    # Neurological
    'cpot': {'type': 'integer'},
    'rass': {'type': 'integer'},
    'glasgow': {'type': 'integer'},
    'reflejo_pupilar': {'type': 'boolean'},
    'reflejo_corneal': {'type': 'boolean'},
    'reflejo_tusigeno': {'type': 'boolean'},
    'rots': {'type': 'text'},
    'pupilas_mm': {'type': 'real'},
    'exploracion_neurologica': {'type': 'text'},
    'imagen_neurologica': {'type': 'text'},
    
    # Hemodynamic
    'mottling': {'type': 'integer'},
    'llenado_capilar': {'type': 'integer'},
    'tas': {'type': 'integer'},
    'tad': {'type': 'integer'},
    'tam': {'type': 'real'},
    'fc': {'type': 'integer'},
    'ekg': {'type': 'text'},
    'exploracion_hemodinamica': {'type': 'text'},
    
    # Ventilatory
    'talla': {'type': 'real'},
    'peso_ideal': {'type': 'real'},
    'fr': {'type': 'integer'},
    'sao2': {'type': 'integer'},
    'disnea': {'type': 'boolean'},
    'o2_suplementario': {'type': 'boolean'},
    'fio2': {'type': 'integer'},
    'modo_ventilatorio': {'type': 'text'},
    'inicio_ventilador': {'type': 'date'},
    'traqueostomia_ingreso': {'type': 'boolean'},
    'numero_tubo': {'type': 'integer'},
    'arcada': {'type': 'real'},
    'vt_psinp': {'type': 'integer'},
    'vt_peso': {'type': 'real'},
    'peep': {'type': 'integer'},
    'relacion_ie': {'type': 'text'},
    'ppico': {'type': 'integer'},
    'pplat': {'type': 'integer'},
    'vol_min': {'type': 'integer'},
    'driving_pressure': {'type': 'integer'},
    'p0_1': {'type': 'real'},
    'nif': {'type': 'integer'},
    'tos': {'type': 'integer'},
    'exploracion_ventilatoria': {'type': 'text'},
    'imagen_ventilatoria': {'type': 'text'},
    'blue': {'type': 'text'},
    'gasometria_fecha': {'type': 'date'},
    'gasometria_ph': {'type': 'real'},
    'gasometria_hco3': {'type': 'real'},
    'gasometria_pco2': {'type': 'real'},
    'gasometria_po2': {'type': 'real'},
    'gasometria_lactato': {'type': 'real'},
    'tobin': {'type': 'real'},
    'pafi': {'type': 'real'},
    'vent_otros': {'type': 'text'},
    
    # Hydro-Renal
    'sonda_vesical': {'type': 'boolean'},
    'peso_estimado': {'type': 'real'},
    'periodo_horas': {'type': 'integer'},
    'diuresis_total': {'type': 'integer'},
    'indice_urinario': {'type': 'real'},
    'ingresos': {'type': 'integer'},
    'egresos': {'type': 'integer'},
    'balance': {'type': 'integer'},
    'balance_global': {'type': 'integer'},
    'bun': {'type': 'real'},
    'urea': {'type': 'real'},
    'creatinina': {'type': 'real'},
    'sodio': {'type': 'real'},
    'potasio': {'type': 'real'},
    'cloro': {'type': 'real'},
    'fosforo': {'type': 'real'},
    'magnesio': {'type': 'real'},
    'calcio': {'type': 'real'},
    'ego': {'type': 'text'},
    'tfg': {'type': 'real'},
    'fena': {'type': 'real'},
    'febun': {'type': 'real'},
    'osmolaridad': {'type': 'real'},
    
    # Gastro-Metabolic
    'imc': {'type': 'real'},
    'peso_ajustado': {'type': 'real'},
    'ayuno': {'type': 'boolean'},
    'gastrostomia_ingreso': {'type': 'boolean'},
    'sonda_levin': {'type': 'boolean'},
    'proteinas_slider': {'type': 'real'},
    'proteinas_requeridas': {'type': 'real'},
    'tipo_nutricion': {'type': 'text'},
    'producto_nutricion': {'type': 'text'},
    'volumen_aporte': {'type': 'integer'},
    'kcal_aporte': {'type': 'integer'},
    'proteinas_aporte': {'type': 'real'},
    'ml_24h_calc': {'type': 'real'},
    'ml_h_calc': {'type': 'real'},
    'kcal_totales_calc': {'type': 'real'},
    'kcal_kg_calc': {'type': 'real'},
    'pct_kcal_calc': {'type': 'real'},
    'glucemia_capilar': {'type': 'integer'},
    'insulina_glargina': {'type': 'real'},
    'insulina_rapida': {'type': 'real'},
    'evacuaciones': {'type': 'integer'},
    'bristol': {'type': 'text'},
    'glucosa_central': {'type': 'real'},
    'bilirrubina_total': {'type': 'real'},
    'bilirrubina_directa': {'type': 'real'},
    'bilirrubina_indirecta': {'type': 'real'},
    'albumina': {'type': 'real'},
    'proteinas_totales': {'type': 'real'},
    'alt': {'type': 'real'},
    'ast': {'type': 'real'},
    'dhl': {'type': 'real'},
    'fosfatasa_alcalina': {'type': 'real'},
    'amilasa': {'type': 'real'},
    'lipasa': {'type': 'real'},
    'exploracion_gastro': {'type': 'text'},
    'drenajes': {'type': 'text'},
    
    # Hematologic-Infectious
    'temperatura': {'type': 'real'},
    'petequias': {'type': 'boolean'},
    'sangrado': {'type': 'boolean'},
    'trombosis': {'type': 'boolean'},
    'leucocitos': {'type': 'real'},
    'neutrofilos': {'type': 'real'},
    'linfocitos': {'type': 'real'},
    'hemoglobina': {'type': 'real'},
    'hematocrito': {'type': 'real'},
    'plaquetas': {'type': 'real'},
    'pcr': {'type': 'real'},
    'pct': {'type': 'real'},
    'vsg': {'type': 'real'},
    'troponina': {'type': 'real'},
    'bnp': {'type': 'real'},
    'dimero_d': {'type': 'real'},
    'tp': {'type': 'real'},
    'ttp': {'type': 'real'},
    'inr': {'type': 'real'},
    'fibrinogeno': {'type': 'real'},
    'exploracion_hema': {'type': 'text'},
    
    # Antecedentes y Comorbilidades (Charlson)
    'padecimiento_actual': {'type': 'text'},
    'evolucion_previa': {'type': 'text'},
    'charlson_edad': {'type': 'integer'},
    'charlson_im': {'type': 'integer'},
    'charlson_evc': {'type': 'integer'},
    'charlson_ep': {'type': 'integer'},
    'charlson_demencia': {'type': 'integer'},
    'charlson_epoc': {'type': 'integer'},
    'charlson_tejido_conectivo': {'type': 'integer'},
    'charlson_ulcera_peptica': {'type': 'integer'},
    'charlson_enfermedad_hepatica_leve': {'type': 'integer'},
    'charlson_enfermedad_hepatica_moderada': {'type': 'integer'},
    'charlson_insuficiencia_renal': {'type': 'integer'},
    'charlson_dmi': {'type': 'integer'},
    'charlson_dmii': {'type': 'integer'},
    'charlson_hemiparesia': {'type': 'integer'},
    'charlson_leucemia': {'type': 'integer'},
    'charlson_linfoma': {'type': 'integer'},
    'charlson_tumor_solido': {'type': 'integer'},
    'charlson_tumor_metastasis': {'type': 'integer'},
    'charlson_sida': {'type': 'integer'},
    'charlson_total': {'type': 'integer'},
    'charlson_mortalidad': {'type': 'text'},
    
    # Initial Assessment
    'diagnostico_ingreso': {'type': 'text'},
    'plan_ingreso': {'type': 'text'},
    'news2_ingreso': {'type': 'integer'},
    'news2_interpretado': {'type': 'text'},
    'sofa_ingreso': {'type': 'integer'},
    'sofa_mortalidad': {'type': 'text'},
    'sofa2_ingreso': {'type': 'integer'},
    'apache2_ingreso': {'type': 'integer'},
    'apache2_mortalidad': {'type': 'text'},
    'saps3_ingreso': {'type': 'integer'},
    'saps3_mortalidad': {'type': 'text'},
    'swift_score': {'type': 'integer'},
    
    # Discharge Data
    'fc_egreso': {'type': 'integer'},
    'fr_egreso': {'type': 'integer'},
    'tas_egreso': {'type': 'integer'},
    'tad_egreso': {'type': 'integer'},
    'tam_egreso': {'type': 'real'},
    'sao2_egreso': {'type': 'integer'},
    'fio2_egreso': {'type': 'integer'},
    'pafi_egreso': {'type': 'real'},
    'temperatura_egreso': {'type': 'real'},
    'hemoglobina_egreso': {'type': 'real'},
    'hematocrito_egreso': {'type': 'real'},
    'leucocitos_egreso': {'type': 'real'},
    'plaquetas_egreso': {'type': 'real'},
    'neutrofilos_egreso': {'type': 'real'},
    'linfocitos_egreso': {'type': 'real'},
    'pcr_egreso': {'type': 'real'},
    'pct_egreso': {'type': 'real'},
    'sodio_egreso': {'type': 'real'},
    'potasio_egreso': {'type': 'real'},
    'cloro_egreso': {'type': 'real'},
    'creatinina_egreso': {'type': 'real'},
    'bun_egreso': {'type': 'real'},
    'urea_egreso': {'type': 'real'},
    'glucosa_egreso': {'type': 'real'},
    'bilirrubina_total_egreso': {'type': 'real'},
    'bilirrubina_directa_egreso': {'type': 'real'},
    'albumina_egreso': {'type': 'real'},
    'gasometria_ph_egreso': {'type': 'real'},
    'gasometria_pco2_egreso': {'type': 'real'},
    'gasometria_po2_egreso': {'type': 'real'},
    'gasometria_hco3_egreso': {'type': 'real'},
    'gasometria_lactato_egreso': {'type': 'real'},
    'fecha_egreso_uci': {'type': 'date'},
    'fecha_egreso_hospital': {'type': 'date'},
    'tipo_egreso': {'type': 'text'},
    'servicio_egreso': {'type': 'text'},
    'fecha_defuncion': {'type': 'date'},
    'fecha_retiro_cvc': {'type': 'date'},
    'fecha_retiro_sonda_urinaria': {'type': 'date'},
    'fecha_extubacion': {'type': 'date'},
    'diagnostico_egreso': {'type': 'text'},
    'plan_egreso': {'type': 'text'},
    'news2_egreso': {'type': 'integer'},
    'sofa_egreso': {'type': 'integer'},
    'sofa2_egreso': {'type': 'integer'},
    'apache2_egreso': {'type': 'integer'},
    'saps_egreso': {'type': 'integer'},
    'condicion_egreso': {'type': 'text'},
    'destino_egreso': {'type': 'text'},
    
    # Nota de Ingreso
    'antecedentes_no_patologicos': {'type': 'text'},
    'antecedentes_patologicos': {'type': 'text'},
    'padecimiento_actual': {'type': 'text'},
    'nota_ingreso_final': {'type': 'text'},
    
    # Status
    'estado': {'type': 'text'}
}

# Dynamic tables configuration
DYNAMIC_TABLES = {
    'medicamentos_neurologicos': 'medicamentos_neurologicos',
    'medicamentos_hemodinamicos': 'medicamentos_hemodinamicos',
    'medicamentos_nefro': 'medicamentos_nefro',
    'medicamentos_gastro': 'medicamentos_gastro',
    'medicacion_hematologica': 'medicacion_hematologica',
    'cultivos': 'cultivos',
    'transfusiones': 'transfusiones'
}


# ============================================================================
# DATA CONVERSION HELPERS
# ============================================================================

def convert_field_value(field_name, value, field_config):
    """Convierte un valor de formulario al tipo de dato apropiado."""
    if value is None or value == '':
        return None
    
    field_type = field_config.get('type', 'text')
    
    try:
        if field_type == 'integer':
            return int(value)
        elif field_type == 'real':
            return float(value)
        elif field_type == 'boolean':
            if isinstance(value, bool):
                return value
            return value.lower() in ('true', '1', 'yes', 'on', 'si', 'sí', 'checked')
        elif field_type == 'date':
            # Mantener como string en formato ISO
            return value
        else:
            return str(value)
    except (ValueError, TypeError):
        return None


def parse_form_data(form_data):
    """Parse form data into patient dictionary."""
    patient_data = {}
    for field_name, config in PATIENT_FIELDS.items():
        if field_name in form_data:
            value = form_data.get(field_name)
            patient_data[field_name] = convert_field_value(field_name, value, config)
    return patient_data


def parse_dynamic_tables_data(form_data):
    """Extrae datos de tablas dinámicas desde el formulario.
    
    Soporta dos formatos:
    1. Arrays planos: neurologicos_medicamento[]
    2. Diccionarios anidados: dynamic_medicamentos_neurologicos[0][medicamento]
    """
    result = {}
    
    # Debug: mostrar todas las claves del formulario
    if hasattr(form_data, 'keys'):
        all_keys = list(form_data.keys())
        dynamic_keys = [k for k in all_keys if 'dynamic' in k.lower() or 'medicamento' in k.lower()]
        if dynamic_keys:
            logger.debug(f"Claves de tablas dinamicas encontradas: {dynamic_keys[:5]}...")
    
    # === FORMATO 2: Diccionarios anidados (nuevo formato del template) ===
    # Procesar medicamentos neurológicos
    meds_neuro = _parse_nested_dynamic_table(form_data, 'dynamic_medicamentos_neurologicos')
    if meds_neuro:
        result['medicamentos_neurologicos'] = meds_neuro
    
    # Procesar medicamentos hemodinámicos
    meds_hemo = _parse_nested_dynamic_table(form_data, 'dynamic_medicamentos_hemodinamicos')
    if meds_hemo:
        result['medicamentos_hemodinamicos'] = meds_hemo
    
    # Procesar medicamentos nefro
    meds_nefro = _parse_nested_dynamic_table(form_data, 'dynamic_medicamentos_nefro')
    if meds_nefro:
        result['medicamentos_nefro'] = meds_nefro
    
    # Procesar medicamentos gastro
    meds_gastro = _parse_nested_dynamic_table(form_data, 'dynamic_medicamentos_gastro')
    if meds_gastro:
        result['medicamentos_gastro'] = meds_gastro
    
    # Procesar medicación hematológica
    meds_hemato = _parse_nested_dynamic_table(form_data, 'dynamic_medicacion_hematologica')
    if meds_hemato:
        result['medicacion_hematologica'] = meds_hemato
    
    # Procesar cultivos
    cultivos = _parse_nested_dynamic_table(form_data, 'dynamic_cultivos')
    if cultivos:
        result['cultivos'] = cultivos
    
    # Procesar transfusiones
    transfusiones = _parse_nested_dynamic_table(form_data, 'dynamic_transfusiones')
    if transfusiones:
        result['transfusiones'] = transfusiones
    
    # === FORMATO 1: Arrays planos (formato antiguo) ===
    # Solo procesar si no se encontraron datos en formato anidado
    
    if 'medicamentos_neurologicos' not in result:
        meds_neuro = []
        medicamentos = form_data.getlist('neurologicos_medicamento[]') if hasattr(form_data, 'getlist') else []
        if medicamentos:
            for i, med in enumerate(medicamentos):
                if med and med.strip():
                    item = {'medicamento': med.strip()}
                    for col in ['unidad', 'dosis', 'fecha_inicio', 'fecha_fin', 'indicacion']:
                        key = f'neurologicos_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    meds_neuro.append(item)
        result['medicamentos_neurologicos'] = meds_neuro
    
    if 'medicamentos_hemodinamicos' not in result:
        meds_hemo = []
        medicamentos = form_data.getlist('hemodinamicos_medicamento[]') if hasattr(form_data, 'getlist') else []
        if medicamentos:
            for i, med in enumerate(medicamentos):
                if med and med.strip():
                    item = {'medicamento': med.strip()}
                    for col in ['unidad', 'dosis_max', 'dosis_min', 'fecha_inicio', 'fecha_fin', 'indicacion']:
                        key = f'hemodinamicos_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    meds_hemo.append(item)
        result['medicamentos_hemodinamicos'] = meds_hemo
    
    if 'medicamentos_nefro' not in result:
        meds_nefro = []
        medicamentos = form_data.getlist('nefro_medicamento[]') if hasattr(form_data, 'getlist') else []
        if medicamentos:
            for i, med in enumerate(medicamentos):
                if med and med.strip():
                    item = {'medicamento': med.strip()}
                    for col in ['unidad', 'dosis', 'fecha_inicio', 'fecha_fin']:
                        key = f'nefro_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    meds_nefro.append(item)
        result['medicamentos_nefro'] = meds_nefro
    
    if 'medicamentos_gastro' not in result:
        meds_gastro = []
        medicamentos = form_data.getlist('gastro_medicamento[]') if hasattr(form_data, 'getlist') else []
        if medicamentos:
            for i, med in enumerate(medicamentos):
                if med and med.strip():
                    item = {'medicamento': med.strip()}
                    for col in ['unidad', 'dosis', 'fecha_inicio', 'fecha_fin']:
                        key = f'gastro_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    meds_gastro.append(item)
        result['medicamentos_gastro'] = meds_gastro
    
    if 'medicacion_hematologica' not in result:
        meds_hemato = []
        medicamentos = form_data.getlist('hematologica_medicamento[]') if hasattr(form_data, 'getlist') else []
        if medicamentos:
            for i, med in enumerate(medicamentos):
                if med and med.strip():
                    item = {'medicamento': med.strip()}
                    for col in ['dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion']:
                        key = f'hematologica_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    meds_hemato.append(item)
        result['medicacion_hematologica'] = meds_hemato
    
    if 'cultivos' not in result:
        cultivos_list = []
        tipos = form_data.getlist('cultivos_tipo[]') if hasattr(form_data, 'getlist') else []
        if tipos:
            for i, tipo in enumerate(tipos):
                if tipo and tipo.strip():
                    item = {'tipo': tipo.strip()}
                    for col in ['fecha', 'resultado', 'sensibilidad', 'resistencia']:
                        key = f'cultivos_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    cultivos_list.append(item)
        result['cultivos'] = cultivos_list
    
    if 'transfusiones' not in result:
        transfusiones_list = []
        componentes = form_data.getlist('transfusiones_componente[]') if hasattr(form_data, 'getlist') else []
        if componentes:
            for i, comp in enumerate(componentes):
                if comp and comp.strip():
                    item = {'componente': comp.strip()}
                    for col in ['dosis_unidades', 'dosis_ml', 'fecha_transfusion', 'reaccion_adversa']:
                        key = f'transfusiones_{col}[]'
                        values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                        if i < len(values):
                            item[col] = values[i]
                    transfusiones_list.append(item)
        result['transfusiones'] = transfusiones_list
    
    # Debug: mostrar resultado
    for key, items in result.items():
        if items:
            logger.debug(f"Tabla {key}: {len(items)} items")
    
    return result


def _parse_nested_dynamic_table(form_data, prefix):
    """Parsea tablas dinámicas en formato diccionario anidado.
    
    Soporta índices numéricos: dynamic_medicamentos_neurologicos[0][medicamento]
    Soporta índice 'new': dynamic_medicamentos_neurologicos[new][medicamento]
    """
    result = []
    
    # Encontrar todos los índices usados (numéricos y 'new')
    indices = set()
    if hasattr(form_data, 'keys'):
        for key in form_data.keys():
            if key.startswith(prefix + '['):
                # Extraer índice: dynamic_medicamentos_neurologicos[0][medicamento] -> 0
                # o dynamic_medicamentos_neurologicos[new][medicamento] -> new
                match = __import__('re').match(rf'{__import__('re').escape(prefix)}\[(\w+)\]', key)
                if match:
                    idx = match.group(1)
                    if idx != 'new':  # Ignorar 'new' aquí, se procesa separado
                        try:
                            indices.add(int(idx))
                        except ValueError:
                            pass
    
    # Para cada índice numérico, extraer los campos
    for idx in sorted(indices):
        item = {}
        has_data = False
        
        if hasattr(form_data, 'keys'):
            for key in form_data.keys():
                pattern = f'{prefix}[{idx}]['
                if key.startswith(pattern):
                    # Extraer nombre del campo
                    field_name = key[len(pattern):-1]  # Quitar prefijo y ]
                    value = form_data.get(key, '')
                    if value and value.strip():
                        item[field_name] = value.strip()
                        has_data = True
        
        if has_data:
            result.append(item)
    
    # Procesar índice 'new' (nuevos registros desde evolución)
    if hasattr(form_data, 'keys'):
        new_item = {}
        new_has_data = False
        for key in form_data.keys():
            pattern = f'{prefix}[new]['
            if key.startswith(pattern):
                field_name = key[len(pattern):-1]
                value = form_data.get(key, '')
                if value and value.strip():
                    new_item[field_name] = value.strip()
                    new_has_data = True
        
        if new_has_data:
            result.append(new_item)
    
    return result


# ============================================================================
    meds_gastro = []
    medicamentos = form_data.getlist('gastro_medicamento[]') if hasattr(form_data, 'getlist') else []
    if medicamentos:
        for i, med in enumerate(medicamentos):
            if med and med.strip():
                item = {'medicamento': med.strip()}
                for col in ['unidad', 'dosis', 'fecha_inicio', 'fecha_fin']:
                    key = f'gastro_{col}[]'
                    values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                    if i < len(values):
                        item[col] = values[i]
                meds_gastro.append(item)
    result['medicamentos_gastro'] = meds_gastro
    
    # Procesar medicación hematológica
    meds_hema = []
    medicamentos = form_data.getlist('hematologica_medicamento[]') if hasattr(form_data, 'getlist') else []
    if medicamentos:
        for i, med in enumerate(medicamentos):
            if med and med.strip():
                item = {'medicamento': med.strip()}
                for col in ['dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion']:
                    key = f'hematologica_{col}[]'
                    values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                    if i < len(values):
                        item[col] = values[i]
                meds_hema.append(item)
    result['medicacion_hematologica'] = meds_hema
    
    # Procesar cultivos
    cultivos = []
    tipos = form_data.getlist('cultivo_tipo[]') if hasattr(form_data, 'getlist') else []
    if tipos:
        for i, tipo in enumerate(tipos):
            if tipo and tipo.strip():
                item = {'tipo': tipo.strip()}
                for col in ['fecha', 'resultado', 'sensibilidad', 'resistencia']:
                    key = f'cultivo_{col}[]'
                    values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                    if i < len(values):
                        item[col] = values[i]
                cultivos.append(item)
    result['cultivos'] = cultivos
    
    # Procesar transfusiones
    transfusiones = []
    componentes = form_data.getlist('transfusion_componente[]') if hasattr(form_data, 'getlist') else []
    if componentes:
        for i, comp in enumerate(componentes):
            if comp and comp.strip():
                item = {'componente': comp.strip()}
                for col in ['dosis_unidades', 'dosis_ml', 'fecha_transfusion', 'reaccion_adversa']:
                    key = f'transfusion_{col}[]'
                    values = form_data.getlist(key) if hasattr(form_data, 'getlist') else []
                    if i < len(values):
                        item[col] = values[i]
                transfusiones.append(item)
    result['transfusiones'] = transfusiones
    
    return result


# ============================================================================
# CORE SAVE FUNCTIONS - Flujo corregido
# ============================================================================

def save_patient_with_calculations(patient_data, patient_id=None, is_update=False):
    """
    Flujo unificado de guardado con cálculos automáticos.
    
    PASOS:
    1. Validar datos requeridos
    2. Insertar/actualizar datos crudos (sin scores calculados)
    3. Si es nuevo: obtener ID del registro creado
    4. Calcular todos los campos automáticos
    5. Actualizar registro con cálculos
    6. Si falla: hacer rollback y mostrar error
    
    Args:
        patient_data: Diccionario con datos del paciente
        patient_id: ID del paciente (None para nuevo, int para actualizar)
        is_update: True si es actualización
    
    Returns:
        tuple: (success: bool, patient_id: int/None, message: str, error: str/None)
    """
    try:
        # PASO 1: Validar campos requeridos
        if not patient_data.get('nombre_completo'):
            return False, None, "Faltan campos requeridos", "El nombre completo es obligatorio"
        
        # Validar expediente único
        expediente = patient_data.get('expediente')
        if expediente and check_expediente_exists(expediente, exclude_id=patient_id):
            return False, None, "Expediente duplicado", f"Ya existe otro paciente con el expediente {expediente}"
        
        # Separar datos de tablas dinámicas
        dynamic_data = {}
        for key in list(patient_data.keys()):
            if key in DYNAMIC_TABLES:
                dynamic_data[key] = patient_data.pop(key)
        
        # PASO 2 & 3: Insertar o actualizar datos base
        if is_update and patient_id:
            # Actualizar paciente existente
            update_patient(patient_id, patient_data)
            current_id = patient_id
        else:
            # Insertar nuevo paciente - sin cálculos todavía
            patient_data['estado'] = patient_data.get('estado', 'ingreso')
            current_id = insert_patient(patient_data)
        
        # PASO 4: Calcular campos automáticos con todos los datos
        # Recuperar el registro completo para cálculos
        if is_update and patient_id:
            # Para actualización, combinar datos existentes con nuevos
            existing = get_patient(patient_id) or {}
            calculation_data = {**existing, **patient_data}
        else:
            calculation_data = patient_data.copy()
        
        # Calcular campos computados
        calculated_data = calculate_computed_fields(calculation_data)
        
        # PASO 5: Actualizar con cálculos
        # Extraer solo los campos calculados
        computed_fields = [
            'edad', 'dias_estancia', 'tam', 'imc', 'peso_ideal', 'peso_ajustado',
            'proteinas_requeridas', 'ml_24h_calc', 'kcal_totales_calc',
            'indice_urinario', 'tfg', 'tobin', 'pafi', 'balance', 'vt_peso',
            'news2_ingreso', 'news2_interpretado', 'sofa_ingreso', 'sofa_mortalidad',
            'sofa2_ingreso', 'apache2_ingreso', 'apache2_mortalidad',
            'saps3_ingreso', 'saps3_mortalidad', 'swift_score'
        ]
        
        update_data = {k: calculated_data.get(k) for k in computed_fields if calculated_data.get(k) is not None}
        
        if update_data:
            update_patient(current_id, update_data)
        
        # Guardar tablas dinámicas
        if dynamic_data:
            save_dynamic_tables_from_dict(current_id, dynamic_data)
        
        # PASO 5.5: Crear evolución de ingreso automáticamente (solo para pacientes nuevos)
        if not is_update:
            try:
                # Calcular TAM si no está presente
                tam = calculation_data.get('tam')
                if not tam and calculation_data.get('tas') and calculation_data.get('tad'):
                    from modules.calculations import calc_tam
                    tam = calc_tam(calculation_data.get('tas'), calculation_data.get('tad'))
                
                # Calcular PaFi si no está presente
                pafi = calculation_data.get('pafi')
                if not pafi and calculation_data.get('gasometria_po2') and calculation_data.get('fio2'):
                    from modules.calculations import calc_pafi
                    pafi = calc_pafi(calculation_data.get('gasometria_po2'), calculation_data.get('fio2'))
                
                # Crear nota de ingreso básica con datos disponibles
                nota_ingreso = f"""NOTA DE INGRESO UCI

Paciente: {calculation_data.get('nombre_completo', 'N/A')}
Edad: {calculation_data.get('edad', 'N/A')} años, Sexo: {calculation_data.get('sexo', 'N/A')}
Expediente: {calculation_data.get('expediente', 'N/A')}
Fecha de ingreso: {calculation_data.get('fecha_ingreso', date.today().isoformat())}
Diagnóstico: {calculation_data.get('diagnostico_ingreso', 'No especificado')}

SIGNOS VITALES:
FC: {calculation_data.get('fc', 'N/A')} lpm
FR: {calculation_data.get('fr', 'N/A')} rpm
TAS: {calculation_data.get('tas', 'N/A')} mmHg
TAD: {calculation_data.get('tad', 'N/A')} mmHg
TAM: {tam or 'N/A'} mmHg
Temp: {calculation_data.get('temperatura', 'N/A')} °C
SpO2: {calculation_data.get('sao2', 'N/A')}%
FiO2: {calculation_data.get('fio2', 'N/A')}%
Glasgow: {calculation_data.get('glasgow', 'N/A')}

VENTILACIÓN:
Modo: {calculation_data.get('modo_ventilatorio', 'No ventilado')}
VT: {calculation_data.get('vt_psinp', 'N/A')} mL
PEEP: {calculation_data.get('peep', 'N/A')} cmH2O
Ppico: {calculation_data.get('ppico', 'N/A')} cmH2O
Pplat: {calculation_data.get('pplat', 'N/A')} cmH2O
PaFi: {pafi or 'N/A'} mmHg

LABORATORIOS INICIALES:
Hemoglobina: {calculation_data.get('hemoglobina', 'N/A')} g/dL
Leucocitos: {calculation_data.get('leucocitos', 'N/A')} x10^9/L
Plaquetas: {calculation_data.get('plaquetas', 'N/A')} x10^9/L
Glucosa: {calculation_data.get('glucosa_central', calculation_data.get('glucemia_capilar', 'N/A'))} mg/dL
Creatinina: {calculation_data.get('creatinina', 'N/A')} mg/dL
BUN: {calculation_data.get('bun', 'N/A')} mg/dL
Sodio: {calculation_data.get('sodio', 'N/A')} mEq/L
Potasio: {calculation_data.get('potasio', 'N/A')} mEq/L
pH: {calculation_data.get('gasometria_ph', 'N/A')}
Lactato: {calculation_data.get('gasometria_lactato', 'N/A')} mmol/L

PLAN:
{calculation_data.get('plan_ingreso', '1. Monitoreo continuo\n2. Manejo según protocolo')}
"""
                
                evolution_data = {
                    'fecha': calculation_data.get('fecha_ingreso') or date.today().isoformat(),
                    'hora': datetime.now().strftime('%H:%M'),
                    'tipo': 'ingreso',
                    'nota': nota_ingreso,
                    'plan': calculation_data.get('plan_ingreso', ''),
                    # Copiar signos vitales
                    'fc': calculation_data.get('fc'),
                    'fr': calculation_data.get('fr'),
                    'tas': calculation_data.get('tas'),
                    'tad': calculation_data.get('tad'),
                    'tam': tam,
                    'temperatura': calculation_data.get('temperatura'),
                    'spo2': calculation_data.get('sao2'),
                    'fio2': calculation_data.get('fio2'),
                    'glasgow': calculation_data.get('glasgow'),
                    'rass': calculation_data.get('rass'),
                    # Copiar ventilación
                    'modo_ventilatorio': calculation_data.get('modo_ventilatorio'),
                    'vt_psinp': calculation_data.get('vt_psinp'),
                    'peep': calculation_data.get('peep'),
                    'ppico': calculation_data.get('ppico'),
                    'pplat': calculation_data.get('pplat'),
                    'pafi': pafi,
                    # Copiar laboratorios
                    'hemoglobina': calculation_data.get('hemoglobina'),
                    'hematocrito': calculation_data.get('hematocrito'),
                    'leucocitos': calculation_data.get('leucocitos'),
                    'neutrofilos': calculation_data.get('neutrofilos'),
                    'linfocitos': calculation_data.get('linfocitos'),
                    'plaquetas': calculation_data.get('plaquetas'),
                    'glucosa': calculation_data.get('glucosa_central') or calculation_data.get('glucemia_capilar'),
                    'creatinina': calculation_data.get('creatinina'),
                    'urea': calculation_data.get('urea'),
                    'bun': calculation_data.get('bun'),
                    'sodio': calculation_data.get('sodio'),
                    'potasio': calculation_data.get('potasio'),
                    'cloro': calculation_data.get('cloro'),
                    'calcio': calculation_data.get('calcio'),
                    'magnesio': calculation_data.get('magnesio'),
                    'fosforo': calculation_data.get('fosforo'),
                    'ph': calculation_data.get('gasometria_ph'),
                    'pco2': calculation_data.get('gasometria_pco2'),
                    'po2': calculation_data.get('gasometria_po2'),
                    'hco3': calculation_data.get('gasometria_hco3'),
                    'lactato': calculation_data.get('gasometria_lactato'),
                    # Copiar balance hídrico
                    'ingresos': calculation_data.get('ingresos'),
                    'egresos': calculation_data.get('egresos'),
                    'diuresis': calculation_data.get('diuresis_total'),
                    'balance': calculation_data.get('balance'),
                    # Scores
                    'news2': calculation_data.get('news2_ingreso'),
                    'sofa': calculation_data.get('sofa_ingreso'),
                    'apache2': calculation_data.get('apache2_ingreso'),
                }
                
                # Limpiar None values
                evolution_data = {k: v for k, v in evolution_data.items() if v is not None}
                
                evolution_id = create_evolution(current_id, evolution_data)
                print(f"✅ Evolución de ingreso creada para paciente {current_id}, evolución ID: {evolution_id}")
            except Exception as e:
                # No fallar si no se puede crear la evolución, solo loggear
                print(f"⚠️ Warning: No se pudo crear evolución de ingreso: {e}")
                import traceback
                traceback.print_exc()
        
        # PASO 6: Éxito
        action = "actualizado" if is_update else "creado"
        return True, current_id, f"Paciente {action} exitosamente", None
        
    except Exception as e:
        # Si hay error, no se hizo commit (las funciones de db hacen rollback automático)
        return False, None, "Error al guardar paciente", str(e)


def get_latest_evolution_id(patient_id):
    """Obtiene el ID de la evolución más reciente de un paciente."""
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT id FROM evoluciones WHERE patient_id = %s ORDER BY created_at DESC LIMIT 1",
                (patient_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except:
        return None


def get_last_balance_global(patient_id):
    """Obtiene el último balance_global de un paciente (manual o calculado).
    
    Returns:
        int or None: Último balance_global registrado
    """
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                """SELECT balance_global, balance, created_at 
                   FROM evoluciones 
                   WHERE patient_id = %s AND balance_global IS NOT NULL
                   ORDER BY created_at DESC 
                   LIMIT 1""",
                (patient_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]  # balance_global
            return None
    except:
        return None


def calculate_balance_global(patient_id, current_balance, manual_balance_global=None):
    """Calcula el balance_global para una nueva evolución.
    
    Lógica:
    1. Si usuario proporciona balance_global manual → usar ese valor
    2. Si no → obtener último balance_global + balance_actual
    3. Si no hay evolución previa → usar balance_actual (o 0 si es None)
    
    Args:
        patient_id: ID del paciente
        current_balance: Balance calculado de esta evolución
        manual_balance_global: Valor manual del usuario (opcional)
    
    Returns:
        int: balance_global calculado o manual
    """
    # Si usuario editó manualmente, usar ese valor
    if manual_balance_global is not None:
        return manual_balance_global
    
    # Obtener último balance_global
    last_global = get_last_balance_global(patient_id)
    
    if last_global is not None and current_balance is not None:
        return last_global + current_balance
    elif current_balance is not None:
        return current_balance
    elif last_global is not None:
        return last_global
    else:
        return 0


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'sinapsid-dma',
        'version': '1.0.0'
    })


# ============================================================================
# AUTH ROUTES - Landing page con autenticación
# ============================================================================

@app.route('/')
def landing():
    """Landing page - página pública de inicio."""
    # Si ya está autenticado, redirigir al dashboard
    session_token = session.get('session_token')
    if session_token:
        from modules.auth import validate_session
        if validate_session(session_token):
            return redirect(url_for('dashboard'))
    
    # Obtener estadísticas reales de la base de datos
    from modules.database import get_db_connection
    
    stats = {
        'centers': 0,
        'contributors': 0,
        'patients': 0
    }
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Contar centros (instituciones únicas)
            cursor.execute("SELECT COUNT(DISTINCT institution) FROM users WHERE institution IS NOT NULL")
            stats['centers'] = cursor.fetchone()[0]
            
            # Contar contribuidores (usuarios totales)
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['contributors'] = cursor.fetchone()[0]
            
            # Contar pacientes
            cursor.execute("SELECT COUNT(*) FROM patients")
            stats['patients'] = cursor.fetchone()[0]
    except:
        pass  # Si hay error, mostrar 0
    
    return render_template('landing.html', stats=stats)


@app.route('/auth/login', methods=['POST'])
def login():
    """API endpoint para login."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    
    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')
    
    if not username_or_email or not password:
        return jsonify({'error': 'Usuario/email y contraseña requeridos'}), 400
    
    user = authenticate_user(username_or_email, password)
    if not user:
        return jsonify({'error': 'Credenciales inválidas'}), 401
    
    # Crear sesión
    session_token = create_session(
        user['id'],
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    
    session['session_token'] = session_token
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'institution': user['institution'],
            'role': user['role']
        }
    })


@app.route('/auth/register', methods=['POST'])
def register():
    """API endpoint para registro."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    
    required = ['username', 'email', 'password', 'institution']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Campo requerido: {field}'}), 400
    
    # Crear usuario
    user_id = create_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        full_name=data.get('full_name'),
        institution=data['institution'],
        role=data.get('role', 'user')
    )
    
    if not user_id:
        return jsonify({'error': 'No se pudo crear el usuario. El username o email ya existe.'}), 409
    
    return jsonify({
        'success': True,
        'message': 'Usuario creado exitosamente. Por favor inicie sesión.',
        'user_id': user_id
    })


@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint."""
    session_token = session.get('session_token')
    if session_token:
        invalidate_session(session_token)
    
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('landing'))


@app.route('/mods')
@login_required
def mods():
    """Página de Mods - Herramientas y calculadoras clínicas."""
    return render_template('mods.html')


@app.route('/api/beta/apply', methods=['POST'])
def beta_apply():
    """API endpoint para aplicaciones beta."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    
    required_fields = ['institution', 'institution_type', 'contact_name', 'role', 'email', 'country', 'use_case']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Campo requerido: {field}'}), 400
    
    # Generar código de referencia
    import secrets
    ref_code = f"SYN-{datetime.now().year}-{secrets.token_hex(2).upper()}"
    data['ref_code'] = ref_code
    
    app_id = save_beta_application(data)
    
    if app_id:
        return jsonify({
            'success': True,
            'ref_code': ref_code,
            'message': 'Aplicación recibida correctamente'
        })
    else:
        return jsonify({'error': 'Error al guardar la aplicación'}), 500


@app.route('/auth/setup', methods=['GET'])
def auth_setup():
    """Página para crear usuario admin inicial (solo para setup)."""
    return render_template('auth_setup.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard - List all patients (requiere autenticación)."""
    active_patients = get_all_patients(status='ingreso')
    discharged_patients = get_all_patients(status='egreso')
    
    # Pasar info del usuario actual
    user = request.current_user
    
    # Aplicar máscara de privacidad según institución del usuario
    user_institution = user.get('institution', '')
    active_patients = mask_patient_data(active_patients, user_institution)
    discharged_patients = mask_patient_data(discharged_patients, user_institution)
    
    return render_template('patients.html', 
                         active_patients=active_patients,
                         discharged_patients=discharged_patients,
                         current_user=user)


@app.route('/api/patient/<patient_id>/complete')
@login_required
@login_required
def get_patient_complete(patient_id):
    """Obtener todos los datos completos de un paciente para exportación."""
    try:
        # Obtener datos del paciente
        patient = get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Paciente no encontrado'}), 404
        
        # Obtener evoluciones
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM evoluciones WHERE patient_id = %s ORDER BY fecha DESC", (patient_id,))
            columns = [desc[0] for desc in cur.description]
            evolutions = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
        
        # Obtener cultivos
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM cultivos WHERE patient_id = %s ORDER BY fecha DESC", (patient_id,))
            columns = [desc[0] for desc in cur.description]
            cultivos = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
        
        return jsonify({
            'patient': patient,
            'evoluciones': evolutions,
            'cultivos': cultivos
        })
    except Exception as e:
        logger.error(f"Error obteniendo datos completos del paciente {patient_id}: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/patient/new', methods=['GET', 'POST'])
@login_required
def new_patient():
    """Create a new patient - CON FLUJO CORREGIDO."""
    if request.method == 'POST':
        patient_data = parse_form_data(request.form)
        
        # Agregar tablas dinámicas
        dynamic_data = parse_dynamic_tables_data(request.form)
        patient_data.update(dynamic_data)
        
        # Establecer fecha de ingreso si no está presente
        if not patient_data.get('fecha_ingreso'):
            patient_data['fecha_ingreso'] = date.today().isoformat()
        
        # Usar flujo unificado de guardado
        success, patient_id, message, error = save_patient_with_calculations(
            patient_data, 
            patient_id=None, 
            is_update=False
        )
        
        if success:
            flash(message, 'success')
            # Redirigir a la evolución recién creada para edición
            evolution_id = get_latest_evolution_id(patient_id)
            if evolution_id:
                return redirect(url_for('edit_evolution', id=patient_id, evo_id=evolution_id))
            else:
                return redirect(url_for('view_patient', id=patient_id))
        else:
            flash(f"{message}: {error}", 'error')
    
    return render_template('patient_form.html', patient=None, mode='new')


@app.route('/patient/<int:id>')
@login_required
def view_patient(id):
    """View patient details."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    # Aplicar máscara de privacidad según institución del usuario
    user = request.current_user
    user_institution = user.get('institution', '')
    patient = mask_patient_data(patient, user_institution)
    
    # Get dynamic data
    medicamentos = {
        'neurologicos': get_dynamic_items('medicamentos_neurologicos', id),
        'hemodinamicos': get_dynamic_items('medicamentos_hemodinamicos', id),
        'nefro': get_dynamic_items('medicamentos_nefro', id),
        'gastro': get_dynamic_items('medicamentos_gastro', id),
        'hematologica': get_dynamic_items('medicacion_hematologica', id)
    }
    cultivos = get_dynamic_items('cultivos', id)
    transfusiones = get_dynamic_items('transfusiones', id)
    evoluciones = get_evolutions(id, limit=50)
    
    # Enriquecer evoluciones con texto libre
    from modules.database import get_texto_libre
    for evo in evoluciones:
        evo['texto_libre'] = get_texto_libre(evo['id'])
    
    return render_template('patient_view.html',
                         patient=patient,
                         medicamentos=medicamentos,
                         cultivos=cultivos,
                         transfusiones=transfusiones,
                         evoluciones=evoluciones)


@app.route('/patient/<int:id>/notes-view')
@login_required
def patient_notes_view(id):
    """Vista simplificada de solo las evoluciones/notas del paciente."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    evoluciones = get_evolutions(id, limit=50)
    
    return render_template('patient_notes_view.html',
                         patient=patient,
                         evoluciones=evoluciones)


@app.route('/patient/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(id):
    """Edit patient data - CON FLUJO CORREGIDO."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        patient_data = parse_form_data(request.form)
        
        # Agregar tablas dinámicas
        dynamic_data = parse_dynamic_tables_data(request.form)
        patient_data.update(dynamic_data)
        
        # Usar flujo unificado de guardado
        success, patient_id, message, error = save_patient_with_calculations(
            patient_data, 
            patient_id=id, 
            is_update=True
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('view_patient', id=id))
        else:
            flash(f"{message}: {error}", 'error')
    
    return render_template('patient_form.html', patient=patient, mode='edit')


@app.route('/patient/<int:id>/evolution', methods=['GET', 'POST'])
@login_required
def add_evolution(id):
    """Add daily evolution for a patient."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Helper: limpiar strings vacíos a None
        app.logger.debug(f"p0_1 raw: {request.form.get('p0_1')}")
        def _clean(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.strip()
                if val == '' or val.lower() == 'none':
                    return None
                # Intentar convertir a número si parece número
                try:
                    if '.' in val:
                        return float(val)
                    return int(val)
                except ValueError:
                    return val  # Mantener como string si no es número
            return val

        evolution_data = {
            'fecha': request.form.get('fecha', date.today().isoformat()),
            'hora': request.form.get('hora'),
            'fc': _clean(request.form.get('fc')),
            'fr': _clean(request.form.get('fr')),
            'tas': _clean(request.form.get('tas')),
            'tad': _clean(request.form.get('tad')),
            'tam': _clean(request.form.get('tam')),
            'temperatura': _clean(request.form.get('temperatura')),
            'spo2': _clean(request.form.get('spo2')),
            'fio2': _clean(request.form.get('fio2')),
            'safio2': _clean(request.form.get('safio2')),
            'pafi': _clean(request.form.get('pafi')),
            'glasgow': _clean(request.form.get('glasgow')),
            'rass': _clean(request.form.get('rass')),
            'modo_ventilatorio': request.form.get('modo_ventilatorio'),
            'vt_psinp': _clean(request.form.get('vt_psinp')),
            'peep': _clean(request.form.get('peep')),
            'ppico': _clean(request.form.get('ppico')),
            'pplat': _clean(request.form.get('pplat')),
            'nif': _clean(request.form.get('nif')),
            'driving_pressure': _clean(request.form.get('driving_pressure')),
            'compliance': _clean(request.form.get('compliance')),
            'p0_1': _clean(request.form.get('p0_1')),
            'tobin': _clean(request.form.get('tobin')),
            'glucosa': _clean(request.form.get('glucosa')),
            'sodio': _clean(request.form.get('sodio')),
            'potasio': _clean(request.form.get('potasio')),
            'cloro': _clean(request.form.get('cloro')),
            'calcio': _clean(request.form.get('calcio')),
            'magnesio': _clean(request.form.get('magnesio')),
            'fosforo': _clean(request.form.get('fosforo')),
            'creatinina': _clean(request.form.get('creatinina')),
            'urea': _clean(request.form.get('urea')),
            'bun': _clean(request.form.get('bun')),
            # Balance de líquidos
            'ingresos': _clean(request.form.get('ingresos')),
            'egresos': _clean(request.form.get('egresos')),
            'diuresis': _clean(request.form.get('diuresis')),
            'drenajes': _clean(request.form.get('drenajes')),
            'balance': _clean(request.form.get('balance')),
            'balance_global': _clean(request.form.get('balance_global')),
            # Laboratorios adicionales
            'hemoglobina': _clean(request.form.get('hemoglobina')),
            'hematocrito': _clean(request.form.get('hematocrito')),
            'leucocitos': _clean(request.form.get('leucocitos')),
            'neutrofilos': _clean(request.form.get('neutrofilos')),
            'linfocitos': _clean(request.form.get('linfocitos')),
            'plaquetas': _clean(request.form.get('plaquetas')),
            'pcr': _clean(request.form.get('pcr')),
            'pct': _clean(request.form.get('pct')),
            'vsg': _clean(request.form.get('vsg')),
            'ph': _clean(request.form.get('ph')),
            'pco2': _clean(request.form.get('pco2')),
            'po2': _clean(request.form.get('po2')),
            'hco3': _clean(request.form.get('hco3')),
            'lactato': _clean(request.form.get('lactato')),
            # Coagulación
            'tp': _clean(request.form.get('tp')),
            'ttp': _clean(request.form.get('ttp')),
            'inr': _clean(request.form.get('inr')),
            'fibrinogeno': _clean(request.form.get('fibrinogeno')),
            'dimero_d': _clean(request.form.get('dimero_d')),
            # Marcadores cardíacos
            'troponina': _clean(request.form.get('troponina')),
            'bnp': _clean(request.form.get('bnp')),
            # Función hepática
            'bilirrubina_total': _clean(request.form.get('bilirrubina_total')),
            'bilirrubina_directa': _clean(request.form.get('bilirrubina_directa')),
            'bilirrubina_indirecta': _clean(request.form.get('bilirrubina_indirecta')),
            'albumina': _clean(request.form.get('albumina')),
            'alt': _clean(request.form.get('alt')),
            'ast': _clean(request.form.get('ast')),
            'dhl': _clean(request.form.get('dhl')),
            'fosfatasa_alcalina': _clean(request.form.get('fosfatasa_alcalina')),
            'amilasa': _clean(request.form.get('amilasa')),
            'lipasa': _clean(request.form.get('lipasa')),
            # Balance calculado
            'balance': _clean(request.form.get('balance')),
            'balance_global': _clean(request.form.get('balance_global')),
            'indice_urinario': _clean(request.form.get('indice_urinario')),
            # Sonda urinaria
            'sonda_urinaria': request.form.get('sonda_urinaria') == 'on' or request.form.get('sonda_urinaria') == 'true',
            'dias_sonda_urinaria': _clean(request.form.get('dias_sonda_urinaria')),
            'fecha_colocacion_sonda_urinaria': request.form.get('fecha_colocacion_sonda_urinaria') or None,
            'fecha_retiro_sonda_urinaria': request.form.get('fecha_retiro_sonda_urinaria') or None,
            # Catéter CVC
            'cateter_cvc': request.form.get('cateter_cvc') == 'on' or request.form.get('cateter_cvc') == 'true',
            'dias_cvc': _clean(request.form.get('dias_cvc')),
            'fecha_colocacion_cvc': request.form.get('fecha_colocacion_cvc') or None,
            'fecha_retiro_cvc': request.form.get('fecha_retiro_cvc') or None,
            # Sonda Endopleural
            'sonda_endopleural': request.form.get('sonda_endopleural') == 'on' or request.form.get('sonda_endopleural') == 'true',
            'dias_endopleural': _clean(request.form.get('dias_endopleural')),
            'fecha_colocacion_endopleural': request.form.get('fecha_colocacion_endopleural') or None,
            'fecha_retiro_endopleural': request.form.get('fecha_retiro_endopleural') or None,
            # Sonda Nasogástrica
            'sonda_nasogastrica': request.form.get('sonda_nasogastrica') == 'on' or request.form.get('sonda_nasogastrica') == 'true',
            'dias_sng': _clean(request.form.get('dias_sng')),
            'fecha_colocacion_sng': request.form.get('fecha_colocacion_sng') or None,
            'fecha_retiro_sng': request.form.get('fecha_retiro_sng') or None,
            # Tubo Endotraqueal
            'tubo_endotraqueal': request.form.get('tubo_endotraqueal') == 'on' or request.form.get('tubo_endotraqueal') == 'true',
            'dias_ett': _clean(request.form.get('dias_ett')),
            'fecha_colocacion_ett': request.form.get('fecha_colocacion_ett') or None,
            'fecha_retiro_ett': request.form.get('fecha_retiro_ett') or None,
            # Traqueostomía
            'traqueostomia': request.form.get('traqueostomia') == 'on' or request.form.get('traqueostomia') == 'true',
            'dias_traqueostomia': _clean(request.form.get('dias_traqueostomia')),
            'fecha_colocacion_traqueostomia': request.form.get('fecha_colocacion_traqueostomia') or None,
            'fecha_retiro_traqueostomia': request.form.get('fecha_retiro_traqueostomia') or None,
            # Sonda LCR
            'sonda_lcr': request.form.get('sonda_lcr') == 'on' or request.form.get('sonda_lcr') == 'true',
            'dias_sonda_lcr': _clean(request.form.get('dias_sonda_lcr')),
            'fecha_colocacion_lcr': request.form.get('fecha_colocacion_lcr') or None,
            'fecha_retiro_lcr': request.form.get('fecha_retiro_lcr') or None,
            # Catéter Intraventricular
            'cateter_intraventricular': request.form.get('cateter_intraventricular') == 'on' or request.form.get('cateter_intraventricular') == 'true',
            'dias_cateter_intraventricular': _clean(request.form.get('dias_cateter_intraventricular')),
            'fecha_colocacion_cateter_intraventricular': request.form.get('fecha_colocacion_cateter_intraventricular') or None,
            'fecha_retiro_cateter_intraventricular': request.form.get('fecha_retiro_cateter_intraventricular') or None,
            # Gastrostomía
            'gastrostomia': request.form.get('gastrostomia') == 'on' or request.form.get('gastrostomia') == 'true',
            'dias_gastrostomia': _clean(request.form.get('dias_gastrostomia')),
            'fecha_colocacion_gastrostomia': request.form.get('fecha_colocacion_gastrostomia') or None,
            'fecha_retiro_gastrostomia': request.form.get('fecha_retiro_gastrostomia') or None,
            # Línea Arterial
            'linea_arterial': request.form.get('linea_arterial') == 'on' or request.form.get('linea_arterial') == 'true',
            'dias_linea_arterial': _clean(request.form.get('dias_linea_arterial')),
            'fecha_colocacion_linea_arterial': request.form.get('fecha_colocacion_linea_arterial') or None,
            'fecha_retiro_linea_arterial': request.form.get('fecha_retiro_linea_arterial') or None,
            # Catéter de Hemodiálisis
            'cateter_hemodialisis': request.form.get('cateter_hemodialisis') == 'on' or request.form.get('cateter_hemodialisis') == 'true',
            'dias_hemodialisis': _clean(request.form.get('dias_hemodialisis')),
            'fecha_colocacion_hemodialisis': request.form.get('fecha_colocacion_hemodialisis') or None,
            'fecha_retiro_hemodialisis': request.form.get('fecha_retiro_hemodialisis') or None,
            # Notas PSOAS - usar nota_final como nota principal si existe
            'nota': _clean(request.form.get('nota_final') or request.form.get('nota') or None),
            'plan': _clean(request.form.get('plan_nota') or request.form.get('plan') or None),
            'subjetivo': _clean(request.form.get('subjetivo') or None),
            'objetivo': _clean(request.form.get('objetivo') or None),
            'analisis': _clean(request.form.get('analisis') or None),
            # Diagnóstico actual de la evolución
            'diagnostico_actual': request.form.get('diagnostico_actual') or None,
            # Tipo de nota (psoas, ingreso, egreso)
            'tipo': request.form.get('tipo_nota', 'evolucion')
        }
        
        # Calcular balance_global si no viene del formulario (manual)
        if not evolution_data.get('balance_global'):
            current_balance = evolution_data.get('balance')
            manual_global = _clean(request.form.get('balance_global'))  # Podría ser 0
            evolution_data['balance_global'] = calculate_balance_global(
                id, 
                current_balance,
                manual_global if manual_global is not None else None
            )
        
        # Validar rangos clínicos
        validation_result = validate_evolution_data(evolution_data)
        if not validation_result['valid']:
            for error in validation_result['errors']:
                flash(error, 'warning')
            # Continuar guardando igual, pero advertir al usuario
        
        evolution_id = create_evolution(id, evolution_data)
        if evolution_id:
            # Guardar texto libre de la evolucion
            texto_libre = request.form.get('texto_libre', '').strip()
            if texto_libre:
                from modules.database import create_texto_libre
                create_texto_libre(evolution_id, id, texto_libre)
            
            # Guardar tablas dinámicas si se enviaron desde la evolución
            dynamic_data = parse_dynamic_tables_data(request.form)
            
            # Procesar eliminaciones
            delete_dict = {}
            for key in request.form.keys():
                if key.startswith('delete_'):
                    table_name = key[7:-2]  # delete_TABLA[]
                    if table_name:
                        delete_dict[table_name] = request.form.getlist(key)
            
            if dynamic_data or delete_dict:
                save_dynamic_tables_from_dict(id, dynamic_data, delete_dict)
            
            flash('Evolución registrada exitosamente', 'success')
            # Redirigir a la misma página para seguir editando
            return redirect(url_for('add_evolution', id=id))
        else:
            flash('Error al registrar evolución', 'error')
    
    return render_template('evolution_form_v2.html', patient=patient, 
                         evolution=None,
                         today=date.today().isoformat(), 
                         now=datetime.now().strftime('%H:%M'),
                         medicamentos_neurologicos=get_dynamic_items('medicamentos_neurologicos', id),
                         medicamentos_hemodinamicos=get_dynamic_items('medicamentos_hemodinamicos', id),
                         medicamentos_nefro=get_dynamic_items('medicamentos_nefro', id),
                         medicamentos_gastro=get_dynamic_items('medicamentos_gastro', id),
                         medicacion_hematologica=get_dynamic_items('medicacion_hematologica', id),
                         antibioticos=get_dynamic_items('antibioticos', id),
                         cultivos=get_dynamic_items('cultivos', id),
                         transfusiones=get_dynamic_items('transfusiones', id))


@app.route('/patient/<int:id>/evolution/<int:evo_id>/delete', methods=['POST'])
@login_required
def delete_evolution_route(id, evo_id):
    """Eliminar una evolución."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    evolution = get_evolution(evo_id)
    if not evolution or evolution.get('patient_id') != id:
        flash('Evolución no encontrada', 'error')
        return redirect(url_for('view_patient', id=id))
    
    if delete_evolution(evo_id):
        flash('Evolución eliminada correctamente', 'success')
    else:
        flash('Error al eliminar evolución', 'error')
    
    return redirect(url_for('view_patient', id=id))

@app.route('/api/patient/<int:id>/delete', methods=['POST'])
@login_required
def api_delete_patient(id):
    """API para eliminar un paciente y todas sus evoluciones."""
    try:
        patient = get_patient(id)
        if not patient:
            return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404
        
        # Eliminar evoluciones primero
        evoluciones = get_evolutions(id)
        for evo in evoluciones:
            delete_evolution(evo['id'])
        
        # Luego eliminar paciente
        with get_db_cursor() as (cursor, conn):
            cursor.execute("DELETE FROM patients WHERE id = %s", (id,))
            conn.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Paciente ' + patient.get('nombre_completo', '') + ' eliminado correctamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/patient/<int:id>/evolution/<int:evo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_evolution(id, evo_id):
    """Editar una evolución existente."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    evolution = get_evolution(evo_id)
    if not evolution or evolution.get('patient_id') != id:
        flash('Evolución no encontrada', 'error')
        return redirect(url_for('view_patient', id=id))

    
    # Cargar texto libre de la evolucion
    from modules.database import get_texto_libre
    evolution["texto_libre"] = get_texto_libre(evo_id)

    if request.method == 'POST':
        def _clean(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.strip()
                if val == '':
                    return None
                try:
                    if '.' in val:
                        return float(val)
                    return int(val)
                except ValueError:
                    return val
            return val

        evolution_data = {
            'fecha': request.form.get('fecha', date.today().isoformat()),
            'hora': request.form.get('hora'),
            'fc': _clean(request.form.get('fc')),
            'fr': _clean(request.form.get('fr')),
            'tas': _clean(request.form.get('tas')),
            'tad': _clean(request.form.get('tad')),
            'tam': _clean(request.form.get('tam')),
            'temperatura': _clean(request.form.get('temperatura')),
            'spo2': _clean(request.form.get('spo2')),
            'fio2': _clean(request.form.get('fio2')),
            'safio2': _clean(request.form.get('safio2')),
            'pafi': _clean(request.form.get('pafi')),
            'glasgow': _clean(request.form.get('glasgow')),
            'rass': _clean(request.form.get('rass')),
            'modo_ventilatorio': request.form.get('modo_ventilatorio'),
            'vt_psinp': _clean(request.form.get('vt_psinp')),
            'peep': _clean(request.form.get('peep')),
            'ppico': _clean(request.form.get('ppico')),
            'pplat': _clean(request.form.get('pplat')),
            'nif': _clean(request.form.get('nif')),
            'driving_pressure': _clean(request.form.get('driving_pressure')),
            'compliance': _clean(request.form.get('compliance')),
            'p0_1': _clean(request.form.get('p0_1')),
            'tobin': _clean(request.form.get('tobin')),
            'glucosa': _clean(request.form.get('glucosa')),
            'sodio': _clean(request.form.get('sodio')),
            'potasio': _clean(request.form.get('potasio')),
            'cloro': _clean(request.form.get('cloro')),
            'calcio': _clean(request.form.get('calcio')),
            'magnesio': _clean(request.form.get('magnesio')),
            'fosforo': _clean(request.form.get('fosforo')),
            'creatinina': _clean(request.form.get('creatinina')),
            'urea': _clean(request.form.get('urea')),
            'bun': _clean(request.form.get('bun')),
            'ingresos': _clean(request.form.get('ingresos')),
            'egresos': _clean(request.form.get('egresos')),
            'diuresis': _clean(request.form.get('diuresis')),
            'drenajes': _clean(request.form.get('drenajes')),
            'balance': _clean(request.form.get('balance')),
            'balance_global': _clean(request.form.get('balance_global')),
            'balance_global': _clean(request.form.get('balance_global')),
            # Sonda urinaria
            'sonda_urinaria': request.form.get('sonda_urinaria') == 'on' or request.form.get('sonda_urinaria') == 'true',
            'dias_sonda_urinaria': _clean(request.form.get('dias_sonda_urinaria')),
            'fecha_colocacion_sonda_urinaria': request.form.get('fecha_colocacion_sonda_urinaria') or None,
            'fecha_retiro_sonda_urinaria': request.form.get('fecha_retiro_sonda_urinaria') or None,
            # Catéter CVC
            'cateter_cvc': request.form.get('cateter_cvc') == 'on' or request.form.get('cateter_cvc') == 'true',
            'dias_cvc': _clean(request.form.get('dias_cvc')),
            'fecha_colocacion_cvc': request.form.get('fecha_colocacion_cvc') or None,
            'fecha_retiro_cvc': request.form.get('fecha_retiro_cvc') or None,
            # Sonda Endopleural
            'sonda_endopleural': request.form.get('sonda_endopleural') == 'on' or request.form.get('sonda_endopleural') == 'true',
            'dias_endopleural': _clean(request.form.get('dias_endopleural')),
            'fecha_colocacion_endopleural': request.form.get('fecha_colocacion_endopleural') or None,
            'fecha_retiro_endopleural': request.form.get('fecha_retiro_endopleural') or None,
            # Sonda Nasogástrica
            'sonda_nasogastrica': request.form.get('sonda_nasogastrica') == 'on' or request.form.get('sonda_nasogastrica') == 'true',
            'dias_sng': _clean(request.form.get('dias_sng')),
            'fecha_colocacion_sng': request.form.get('fecha_colocacion_sng') or None,
            'fecha_retiro_sng': request.form.get('fecha_retiro_sng') or None,
            # Tubo Endotraqueal
            'tubo_endotraqueal': request.form.get('tubo_endotraqueal') == 'on' or request.form.get('tubo_endotraqueal') == 'true',
            'dias_ett': _clean(request.form.get('dias_ett')),
            'fecha_colocacion_ett': request.form.get('fecha_colocacion_ett') or None,
            'fecha_retiro_ett': request.form.get('fecha_retiro_ett') or None,
            # Traqueostomía
            'traqueostomia': request.form.get('traqueostomia') == 'on' or request.form.get('traqueostomia') == 'true',
            'dias_traqueostomia': _clean(request.form.get('dias_traqueostomia')),
            'fecha_colocacion_traqueostomia': request.form.get('fecha_colocacion_traqueostomia') or None,
            'fecha_retiro_traqueostomia': request.form.get('fecha_retiro_traqueostomia') or None,
            # Sonda LCR
            'sonda_lcr': request.form.get('sonda_lcr') == 'on' or request.form.get('sonda_lcr') == 'true',
            'dias_sonda_lcr': _clean(request.form.get('dias_sonda_lcr')),
            'fecha_colocacion_lcr': request.form.get('fecha_colocacion_lcr') or None,
            'fecha_retiro_lcr': request.form.get('fecha_retiro_lcr') or None,
            # Catéter Intraventricular
            'cateter_intraventricular': request.form.get('cateter_intraventricular') == 'on' or request.form.get('cateter_intraventricular') == 'true',
            'dias_cateter_intraventricular': _clean(request.form.get('dias_cateter_intraventricular')),
            'fecha_colocacion_cateter_intraventricular': request.form.get('fecha_colocacion_cateter_intraventricular') or None,
            'fecha_retiro_cateter_intraventricular': request.form.get('fecha_retiro_cateter_intraventricular') or None,
            # Gastrostomía
            'gastrostomia': request.form.get('gastrostomia') == 'on' or request.form.get('gastrostomia') == 'true',
            'dias_gastrostomia': _clean(request.form.get('dias_gastrostomia')),
            'fecha_colocacion_gastrostomia': request.form.get('fecha_colocacion_gastrostomia') or None,
            'fecha_retiro_gastrostomia': request.form.get('fecha_retiro_gastrostomia') or None,
            # Línea Arterial
            'linea_arterial': request.form.get('linea_arterial') == 'on' or request.form.get('linea_arterial') == 'true',
            'dias_linea_arterial': _clean(request.form.get('dias_linea_arterial')),
            'fecha_colocacion_linea_arterial': request.form.get('fecha_colocacion_linea_arterial') or None,
            'fecha_retiro_linea_arterial': request.form.get('fecha_retiro_linea_arterial') or None,
            # Catéter de Hemodiálisis
            'cateter_hemodialisis': request.form.get('cateter_hemodialisis') == 'on' or request.form.get('cateter_hemodialisis') == 'true',
            'dias_hemodialisis': _clean(request.form.get('dias_hemodialisis')),
            'fecha_colocacion_hemodialisis': request.form.get('fecha_colocacion_hemodialisis') or None,
            'fecha_retiro_hemodialisis': request.form.get('fecha_retiro_hemodialisis') or None,
            'hemoglobina': _clean(request.form.get('hemoglobina')),
            'hematocrito': _clean(request.form.get('hematocrito')),
            'leucocitos': _clean(request.form.get('leucocitos')),
            'neutrofilos': _clean(request.form.get('neutrofilos')),
            'linfocitos': _clean(request.form.get('linfocitos')),
            'plaquetas': _clean(request.form.get('plaquetas')),
            'pcr': _clean(request.form.get('pcr')),
            'pct': _clean(request.form.get('pct')),
            'vsg': _clean(request.form.get('vsg')),
            'ph': _clean(request.form.get('ph')),
            'pco2': _clean(request.form.get('pco2')),
            'po2': _clean(request.form.get('po2')),
            'hco3': _clean(request.form.get('hco3')),
            'lactato': _clean(request.form.get('lactato')),
            'tp': _clean(request.form.get('tp')),
            'ttp': _clean(request.form.get('ttp')),
            'inr': _clean(request.form.get('inr')),
            'fibrinogeno': _clean(request.form.get('fibrinogeno')),
            'dimero_d': _clean(request.form.get('dimero_d')),
            'troponina': _clean(request.form.get('troponina')),
            'bnp': _clean(request.form.get('bnp')),
            'bilirrubina_total': _clean(request.form.get('bilirrubina_total')),
            'bilirrubina_directa': _clean(request.form.get('bilirrubina_directa')),
            'bilirrubina_indirecta': _clean(request.form.get('bilirrubina_indirecta')),
            'albumina': _clean(request.form.get('albumina')),
            'alt': _clean(request.form.get('alt')),
            'ast': _clean(request.form.get('ast')),
            'dhl': _clean(request.form.get('dhl')),
            'fosfatasa_alcalina': _clean(request.form.get('fosfatasa_alcalina')),
            'amilasa': _clean(request.form.get('amilasa')),
            'lipasa': _clean(request.form.get('lipasa')),
            'nota': request.form.get('nota_final') or request.form.get('nota') or None,
            'plan': _clean(request.form.get('plan_nota') or request.form.get('plan') or None),
            'subjetivo': _clean(request.form.get('subjetivo') or None),
            'objetivo': _clean(request.form.get('objetivo') or None),
            'analisis': _clean(request.form.get('analisis') or None),
            'diagnostico_actual': request.form.get('diagnostico_actual') or None,
            'tipo': request.form.get('tipo_nota', 'evolucion'),
            'imagen_estudios': request.form.get('imagen_estudios') or None,
            'ekg_texto': request.form.get('ekg_texto') or None,
            'cultivos_resumen': request.form.get('cultivos_resumen') or None,
            'antibioticos_resumen': request.form.get('antibioticos_resumen') or None,
        }
        
        # Validar rangos clínicos
        validation_result = validate_evolution_data(evolution_data)
        if not validation_result['valid']:
            for error in validation_result['errors']:
                flash(error, 'warning')
        
        if update_evolution(evo_id, evolution_data):
            # Guardar/actualizar texto libre de la evolucion
            texto_libre = request.form.get('texto_libre', '').strip()
            from modules.database import create_texto_libre
            create_texto_libre(evo_id, id, texto_libre)
            
            # Guardar tablas dinámicas si se enviaron desde la evolución
            dynamic_data = parse_dynamic_tables_data(request.form)
            
            # Procesar eliminaciones
            delete_dict = {}
            for key in request.form.keys():
                if key.startswith('delete_'):
                    table_name = key[7:-2]  # delete_TABLA[]
                    if table_name:
                        delete_dict[table_name] = request.form.getlist(key)
            
            if dynamic_data or delete_dict:
                save_dynamic_tables_from_dict(id, dynamic_data, delete_dict)
            
            flash('Evolución actualizada exitosamente', 'success')
            # Redirigir a la misma página para seguir editando
            return redirect(url_for('edit_evolution', id=id, evo_id=evo_id))
        else:
            flash('Error al actualizar evolución', 'error')
    
    return render_template('evolution_form_v2.html', patient=patient, 
                         evolution=evolution,
                         today=evolution.get('fecha', date.today().isoformat()), 
                         now=evolution.get('hora', datetime.now().strftime('%H:%M')),
                         medicamentos_neurologicos=get_dynamic_items('medicamentos_neurologicos', id),
                         medicamentos_hemodinamicos=get_dynamic_items('medicamentos_hemodinamicos', id),
                         medicamentos_nefro=get_dynamic_items('medicamentos_nefro', id),
                         medicamentos_gastro=get_dynamic_items('medicamentos_gastro', id),
                         medicacion_hematologica=get_dynamic_items('medicacion_hematologica', id),
                         antibioticos=get_dynamic_items('antibioticos', id),
                         cultivos=get_dynamic_items('cultivos', id),
                         transfusiones=get_dynamic_items('transfusiones', id))


@app.route('/patient/<int:id>/discharge', methods=['GET', 'POST'])
@login_required
def discharge_patient_route(id):
    """Discharge a patient."""
    patient = get_patient(id)
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        discharge_data = parse_form_data(request.form)
        discharge_data['fecha_egreso_uci'] = request.form.get('fecha_egreso_uci', date.today().isoformat())
        discharge_data['tipo_egreso'] = request.form.get('tipo_egreso')
        discharge_data['condicion_egreso'] = request.form.get('condicion_egreso')
        discharge_data['destino_egreso'] = request.form.get('destino_egreso')
        discharge_data['diagnostico_egreso'] = request.form.get('diagnostico_egreso')
        discharge_data['plan_egreso'] = request.form.get('plan_egreso')
        
        # Calcular TAM de egreso
        if discharge_data.get('tas_egreso') and discharge_data.get('tad_egreso'):
            from modules.calculations import calc_tam
            discharge_data['tam_egreso'] = calc_tam(
                discharge_data['tas_egreso'], 
                discharge_data['tad_egreso']
            )
        
        if discharge_patient(id, discharge_data):
            flash('Paciente dado de alta exitosamente', 'success')
            return redirect(url_for('view_patient', id=id))
        else:
            flash('Error al dar de alta', 'error')
    
    return render_template('discharge_form.html', patient=patient)


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/patient/<int:patient_id>', methods=['GET'])
@login_required
def api_patient(patient_id):
    """API to get patient data."""
    patient = get_patient(patient_id)
    if patient:
        return jsonify(patient)
    return jsonify({'error': 'Paciente no encontrado'}), 404


@app.route('/api/patients', methods=['GET'])
@login_required
def api_patients():
    """API to get all patients."""
    status = request.args.get('status')
    patients = get_all_patients(status=status)
    return jsonify(patients)


@app.route('/api/patient/<int:patient_id>/medicamentos/<category>', methods=['GET', 'POST'])
@login_required
def api_medicamentos(patient_id, category):
    """API for medicamentos CRUD operations."""
    table_map = {
        'neurologicos': 'medicamentos_neurologicos',
        'hemodinamicos': 'medicamentos_hemodinamicos',
        'nefro': 'medicamentos_nefro',
        'gastro': 'medicamentos_gastro',
        'hematologica': 'medicacion_hematologica'
    }
    
    if category not in table_map:
        return jsonify({'error': 'Categoría inválida'}), 400
    
    table_name = table_map[category]
    
    if request.method == 'GET':
        from modules.database import get_dynamic_items
        items = get_dynamic_items(table_name, patient_id)
        return jsonify(items)
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        from modules.database import create_dynamic_item
        item_id = create_dynamic_item(table_name, patient_id, data)
        if item_id:
            return jsonify({'id': item_id, 'success': True}), 201
        return jsonify({'error': 'Error al crear medicamento'}), 400


@app.route('/api/calculate/scores', methods=['POST'])
@login_required
def api_calculate_scores():
    """Calculate all prognostic scores from patient data."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON con datos del paciente'}), 400
    
    try:
        scores = calculate_all_scores(data)
        return jsonify({
            'success': True,
            'scores': scores
        })
    except Exception as e:
        return jsonify({'error': f'Error al calcular scores: {str(e)}'}), 400


@app.route('/api/calculate/field', methods=['POST'])
@login_required
def api_calculate_field():
    """Calculate a specific field value."""
    from modules.calculations import (
        calc_tam, calc_imc, calc_peso_ideal, calc_peso_ajustado,
        calc_pafi, calc_tobin, calc_indice_urinario, calc_tfg
    )
    
    data = request.get_json()
    if not data or 'field' not in data:
        return jsonify({'error': 'Se requiere campo "field"'}), 400
    
    field = data.get('field')
    
    try:
        if field == 'tam':
            tas = data.get('tas')
            tad = data.get('tad')
            if tas is None or tad is None:
                return jsonify({'error': 'Se requieren tas y tad'}), 400
            value = calc_tam(tas, tad)
            return jsonify({'success': True, 'field': field, 'value': value, 'formula': '(2*TAD+TAS)/3'})
        
        elif field == 'imc':
            peso = data.get('peso')
            talla = data.get('talla')
            if peso is None or talla is None:
                return jsonify({'error': 'Se requieren peso y talla'}), 400
            value = calc_imc(peso, talla)
            return jsonify({'success': True, 'field': field, 'value': value, 'formula': 'peso/talla²'})
        
        elif field == 'peso_ideal':
            talla = data.get('talla')
            sexo = data.get('sexo')
            if talla is None or sexo is None:
                return jsonify({'error': 'Se requieren talla y sexo'}), 400
            value = calc_peso_ideal(talla, sexo)
            return jsonify({'success': True, 'field': field, 'value': value, 'formula': 'Devine'})
        
        elif field == 'pafi':
            pao2 = data.get('pao2')
            fio2 = data.get('fio2')
            if pao2 is None or fio2 is None:
                return jsonify({'error': 'Se requieren pao2 y fio2'}), 400
            value = calc_pafi(pao2, fio2)
            return jsonify({'success': True, 'field': field, 'value': value, 'formula': 'PaO2/(FiO2/100)'})
        
        else:
            return jsonify({'error': f'Campo "{field}" no soportado'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Error al calcular {field}: {str(e)}'}), 400


@app.route('/generate-note')
@login_required
def generate_note_page():
    """Page for generating clinical notes."""
    patients = get_all_patients(status='ingreso')
    templates = note_generator.get_templates()
    return render_template('generate_note.html', patients=patients, templates=templates)


@app.route('/api/generate-note', methods=['POST'])
@login_required
def api_generate_note():
    """Generate a clinical note from template."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON con datos'}), 400
    
    patient_id = data.get('patient_id')
    template_id = data.get('template_id')
    formato = data.get('format')
    form_data = data.get('form_data', {})  # Datos del formulario actual (evolucion, ingreso, egreso)
    
    if not patient_id:
        return jsonify({'error': 'Se requiere patient_id'}), 400
    
    # Si viene formato (nuevo dropdown unificado), usar generador específico
    if formato:
        return generate_note_by_format(patient_id, formato, form_data)
    
    # Si viene template_id, usar el generador legacy de templates
    if not template_id:
        return jsonify({'error': 'Se requiere template_id o format'}), 400
    
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    # Get dynamic data
    patient_data = dict(patient)
    patient_data['medicamentos_neurologicos'] = get_dynamic_items('medicamentos_neurologicos', patient_id)
    patient_data['medicamentos_hemodinamicos'] = get_dynamic_items('medicamentos_hemodinamicos', patient_id)
    patient_data['medicamentos_nefro'] = get_dynamic_items('medicamentos_nefro', patient_id)
    patient_data['medicamentos_gastro'] = get_dynamic_items('medicamentos_gastro', patient_id)
    patient_data['medicacion_hematologica'] = get_dynamic_items('medicacion_hematologica', patient_id)
    patient_data['cultivos'] = get_dynamic_items('cultivos', patient_id)
    patient_data['transfusiones'] = get_dynamic_items('transfusiones', patient_id)
    
    # Merge con datos del formulario (prioridad a form_data)
    if form_data:
        patient_data.update(form_data)

    # Calcular escalas pronósticas automáticamente
    try:
        from modules.scoring import calcular_todas_las_escalas
        evoluciones = get_evolutions(patient_id, limit=1)
        evolucion_actual = evoluciones[0] if evoluciones else None
        todas_evoluciones = get_evolutions(patient_id, limit=50)
        evolucion_ingreso = todas_evoluciones[-1] if todas_evoluciones else None
        
        resultados_escalas = calcular_todas_las_escalas(
            evolucion_actual, evolucion_ingreso, patient_data
        )
        patient_data["escalas"] = resultados_escalas
        
        escalas_texto = []
        for key, escala in resultados_escalas.items():
            escalas_texto.append(
                f"{escala['escala']}: {escala['score']}/{escala['maximo']} - {escala['riesgo']}"
            )
        patient_data["escalas_texto"] = " | ".join(escalas_texto)
    except Exception as e:
        print(f"Error calculando escalas: {e}")
        patient_data["escalas"] = {}
        patient_data["escalas_texto"] = "Escalas no disponibles"

    
    try:
        note_text = note_generator.generate(template_id, patient_data)
        template = note_generator.get_template(template_id)
        template_title = template['titulo'] if template else template_id
        
        return jsonify({
            'success': True,
            'note': note_text,
            'template_title': template_title,
            'patient_id': patient_id
        })
    except Exception as e:
        return jsonify({'error': f'Error al generar nota: {str(e)}'}), 500


def generate_note_by_format(patient_id, formato, form_data):
    """Genera nota según el formato seleccionado en el dropdown unificado.
    
    Para escalas pronósticas, usa siempre la información más reciente del paciente.
    """
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404
    
    # Obtener la evolución más reciente para cálculos actualizados
    evoluciones = get_evolutions(patient_id, limit=1)
    ultima_evolucion = evoluciones[0] if evoluciones else None
    
    # Calcular escalas con datos más recientes
    from modules.calculations import calculate_all_scores
    
    # Preparar datos para cálculo de escalas
    # PRIORIDAD: form_data (evolución actual) > última_evolución > patient
    # Los datos del formulario actual deben tener prioridad máxima
    calculation_data = {}
    
    # 1. Datos base del paciente (menor prioridad)
    for key, value in patient.items():
        if value is not None and value != '':
            calculation_data[key] = value
    
    # 2. Complementar con última evolución (prioridad media)
    if ultima_evolucion:
        for key, value in ultima_evolucion.items():
            if value is not None and value != '':
                calculation_data[key] = value
    
    # 3. Sobrescribir con datos del formulario actual (mayor prioridad)
    for key, value in form_data.items():
        if value is not None and value != '':
            calculation_data[key] = value
    
    # Calcular escalas
    try:
        scores = calculate_all_scores(calculation_data)
        escalas = {
            'news2': scores['news2']['score'],
            'news2_interpretado': scores['news2']['interpretacion'],
            'sofa2': scores['sofa2']['score'],
            'sofa_mortalidad': scores['sofa']['mortalidad'],
            'apache2': scores['apache2']['score'],
            'apache2_mortalidad': scores['apache2']['mortalidad'],
            'saps3': scores['saps3']['score'],
            'saps3_mortalidad': scores['saps3']['mortalidad'],
            'swift': scores['swift']['score']
        }
    except Exception as e:
        print(f"Error calculando escalas: {e}")
        escalas = {}
    
    if formato == 'psoap':
        # Pasar escalas calculadas al generador PSOAP
        form_data_con_escalas = dict(form_data)
        form_data_con_escalas.update(escalas)
        nota = generate_psoap_note(patient, form_data_con_escalas, ultima_evolucion)
        return jsonify({'success': True, 'note': nota, 'format': 'psoap'})
    
    elif formato == 'ingreso':
        # Pasar datos del formulario actual + paciente + escalas
        datos_ingreso = dict(patient)
        datos_ingreso.update(escalas)
        datos_ingreso.update(form_data)  # form_data tiene prioridad máxima
        if uci_note_disponible():
            nota = generar_nota_ingreso_uci(datos_ingreso, ultima_evolucion)
        else:
            nota = generate_simple_ingreso_note(datos_ingreso)
        return jsonify({'success': True, 'note': nota, 'format': 'ingreso'})
    
    elif formato == 'egreso':
        # Pasar datos del formulario actual + paciente
        datos_egreso = dict(patient)
        datos_egreso.update(form_data)  # form_data tiene prioridad máxima
        nota = generar_nota_egreso(patient, form_data, patient_id)
        return jsonify({'success': True, 'note': nota, 'format': 'egreso'})
    
    elif formato == 'raw':
        nota = generate_raw_note(patient, patient_id)
        return jsonify({'success': True, 'note': nota, 'format': 'raw'})
    
    elif formato == 'resumen':
        return jsonify({'success': False, 'error': 'Formato Resumen no implementado aún'}), 501
    
    else:
        return jsonify({'success': False, 'error': f'Formato desconocido: {formato}'}), 400


# Funciones auxiliares para generación de notas

def generate_psoap_note(patient, form_data, ultima_evolucion=None):
    """Genera nota PSOAP completa usando TODOS los campos disponibles.
    
    Args:
        patient: Datos del paciente (tabla patients)
        form_data: Datos del formulario de evolución actual
        ultima_evolucion: Última evolución registrada (opcional)
    """
    
    # Función auxiliar: busca en form_data -> ultima_evolucion -> patient -> default
    def get_val(key, default=''):
        if form_data.get(key) not in (None, '', []):
            return form_data.get(key)
        if ultima_evolucion and ultima_evolucion.get(key) not in (None, '', []):
            return ultima_evolucion.get(key)
        if patient.get(key) not in (None, '', []):
            return patient.get(key)
        return default
    
    def fmt_date(d):
        """Formatea fecha YYYY-MM-DD -> DD/MM/YYYY"""
        if not d:
            return ''
        try:
            if isinstance(d, str):
                return datetime.strptime(d[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
            if isinstance(d, (date, datetime)):
                return d.strftime('%d/%m/%Y')
        except:
            pass
        return str(d)
    
    def bool_val(v):
        """Convierte cualquier representación de booleano a True/False"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', 'on', '1', 'yes', 'si', 'sí')
        if isinstance(v, (int, float)):
            return bool(v)
        return False
    
    fecha = form_data.get('fecha', date.today().isoformat())
    hora = form_data.get('hora', datetime.now().strftime('%H:%M'))
    
    # ===== TEXTO LIBRE (PSOAP) =====
    subjetivo = form_data.get('subjetivo', 'Sin síntomas subjetivos reportados.')
    objetivo_texto = form_data.get('objetivo', '')
    analisis = form_data.get('analisis', 'Paciente en evolución.')
    plan = form_data.get('plan_nota', '1. Continuar manejo actual\n2. Monitoreo continuo')
    
    # ===== SIGNOS VITALES =====
    fc = get_val('fc')
    fr = get_val('fr')
    tas = get_val('tas')
    tad = get_val('tad')
    tam = get_val('tam')
    temp = get_val('temperatura')
    spo2 = get_val('spo2')
    fio2 = get_val('fio2')
    glasgow = get_val('glasgow')
    rass = get_val('rass')
    cpot = get_val('cpot')
    peso_estimado = get_val('peso_estimado')
    talla = get_val('talla')
    glucosa = get_val('glucosa')
    
    objetivo_parts = []
    
    # Signos vitales
    sv_parts = []
    if fc: sv_parts.append(f"FC {fc} lpm")
    if fr: sv_parts.append(f"FR {fr} rpm")
    if tas: sv_parts.append(f"TAS {tas}")
    if tad: sv_parts.append(f"TAD {tad}")
    if tam: sv_parts.append(f"TAM {tam}")
    if temp: sv_parts.append(f"Temp {temp}°C")
    if spo2: sv_parts.append(f"SpO2 {spo2}%")
    if fio2: sv_parts.append(f"FiO2 {fio2}%")
    if glasgow: sv_parts.append(f"Glasgow {glasgow}")
    if rass: sv_parts.append(f"RASS {rass}")
    if cpot: sv_parts.append(f"CPOT {cpot}")
    if peso_estimado: sv_parts.append(f"Peso {peso_estimado} kg")
    if talla: sv_parts.append(f"Talla {talla} m")
    if glucosa: sv_parts.append(f"Glucosa {glucosa} mg/dL")
    if sv_parts:
        objetivo_parts.append("SIGNOS VITALES: " + ", ".join(sv_parts))
    
    # ===== VENTILACIÓN =====
    modo = get_val('modo_ventilatorio')
    if modo:
        vent_parts = [f"Modo: {modo}"]
        vt_ml = get_val('vt_ml')
        ps_cmh2o = get_val('ps_cmh2o')
        vt_psinp = get_val('vt_psinp')
        if vt_ml: vent_parts.append(f"VT {vt_ml} mL")
        if ps_cmh2o: vent_parts.append(f"PS {ps_cmh2o} cmH2O")
        if not vt_ml and not ps_cmh2o and vt_psinp:
            vent_parts.append(f"VT/PS {vt_psinp}")
        peep = get_val('peep')
        if peep: vent_parts.append(f"PEEP {peep}")
        ppico = get_val('ppico')
        if ppico: vent_parts.append(f"Ppico {ppico}")
        pplat = get_val('pplat')
        if pplat: vent_parts.append(f"Pplat {pplat}")
        driving_pressure = get_val('driving_pressure')
        if driving_pressure: vent_parts.append(f"Driving P {driving_pressure}")
        nif = get_val('nif')
        if nif: vent_parts.append(f"NIF {nif}")
        p0_1 = get_val('p0_1')
        if p0_1: vent_parts.append(f"P0.1 {p0_1}")
        tobin = get_val('tobin')
        if tobin: vent_parts.append(f"Tobin {tobin}")
        compliance = get_val('compliance')
        if compliance: vent_parts.append(f"Compliance {compliance}")
        relacion_ie = get_val('relacion_ie')
        if relacion_ie: vent_parts.append(f"I:E {relacion_ie}")
        vol_min = get_val('vol_min')
        if vol_min: vent_parts.append(f"Vol min {vol_min}")
        safio2 = get_val('safio2')
        if safio2: vent_parts.append(f"SaFiO2 {safio2}")
        pafi = get_val('pafi')
        if pafi: vent_parts.append(f"PaFi {pafi}")
        objetivo_parts.append("VENTILACIÓN: " + ", ".join(vent_parts))
    
    # ===== GASOMETRÍA =====
    gaso_parts = []
    ph = get_val('ph')
    pco2 = get_val('pco2')
    po2 = get_val('po2')
    hco3 = get_val('hco3')
    lactato = get_val('lactato')
    if ph: gaso_parts.append(f"pH {ph}")
    if pco2: gaso_parts.append(f"PCO2 {pco2}")
    if po2: gaso_parts.append(f"PO2 {po2}")
    if hco3: gaso_parts.append(f"HCO3 {hco3}")
    if lactato: gaso_parts.append(f"Lactato {lactato}")
    if gaso_parts:
        objetivo_parts.append("GASOMETRÍA: " + ", ".join(gaso_parts))
    
    # ===== LABORATORIOS COMPLETOS =====
    labs_parts = []
    hb = get_val('hemoglobina')
    if hb: labs_parts.append(f"Hb {hb} g/dL")
    hto = get_val('hematocrito')
    if hto: labs_parts.append(f"Hto {hto}%")
    leu = get_val('leucocitos')
    if leu: labs_parts.append(f"Leu {leu}")
    pla = get_val('plaquetas')
    if pla: labs_parts.append(f"Plaq {pla}")
    neut = get_val('neutrofilos')
    if neut: labs_parts.append(f"Neut {neut}")
    linf = get_val('linfocitos')
    if linf: labs_parts.append(f"Linf {linf}")
    vsg = get_val('vsg')
    if vsg: labs_parts.append(f"VSG {vsg}")
    inr = get_val('inr')
    if inr: labs_parts.append(f"INR {inr}")
    tp = get_val('tp')
    if tp: labs_parts.append(f"TP {tp}")
    ttp = get_val('ttp')
    if ttp: labs_parts.append(f"TTP {ttp}")
    fibrinogeno = get_val('fibrinogeno')
    if fibrinogeno: labs_parts.append(f"Fibrinogeno {fibrinogeno}")
    crea = get_val('creatinina')
    if crea: labs_parts.append(f"Cre {crea}")
    bun = get_val('bun')
    if bun: labs_parts.append(f"BUN {bun}")
    urea = get_val('urea')
    if urea: labs_parts.append(f"Urea {urea}")
    na = get_val('sodio')
    if na: labs_parts.append(f"Na {na}")
    k = get_val('potasio')
    if k: labs_parts.append(f"K {k}")
    cl = get_val('cloro')
    if cl: labs_parts.append(f"Cl {cl}")
    ca = get_val('calcio')
    if ca: labs_parts.append(f"Ca {ca}")
    mg = get_val('magnesio')
    if mg: labs_parts.append(f"Mg {mg}")
    p = get_val('fosforo')
    if p: labs_parts.append(f"P {p}")
    gluc_central = get_val('glucosa_central')
    if gluc_central: labs_parts.append(f"Gluc {gluc_central}")
    pcr = get_val('pcr')
    if pcr: labs_parts.append(f"PCR {pcr}")
    pct = get_val('pct')
    if pct: labs_parts.append(f"PCT {pct}")
    bnp = get_val('bnp')
    if bnp: labs_parts.append(f"BNP {bnp}")
    troponina = get_val('troponina')
    if troponina: labs_parts.append(f"Trop {troponina}")
    dimero_d = get_val('dimero_d')
    if dimero_d: labs_parts.append(f"Dímero D {dimero_d}")
    bili_t = get_val('bilirrubina_total')
    if bili_t: labs_parts.append(f"Bili T {bili_t}")
    bili_d = get_val('bilirrubina_directa')
    if bili_d: labs_parts.append(f"Bili D {bili_d}")
    bili_i = get_val('bilirrubina_indirecta')
    if bili_i: labs_parts.append(f"Bili I {bili_i}")
    albumina = get_val('albumina')
    if albumina: labs_parts.append(f"Alb {albumina}")
    alt = get_val('alt')
    if alt: labs_parts.append(f"ALT {alt}")
    ast = get_val('ast')
    if ast: labs_parts.append(f"AST {ast}")
    dhl = get_val('dhl')
    if dhl: labs_parts.append(f"DHL {dhl}")
    fosf_alc = get_val('fosfatasa_alcalina')
    if fosf_alc: labs_parts.append(f"FA {fosf_alc}")
    amilasa = get_val('amilasa')
    if amilasa: labs_parts.append(f"Amilasa {amilasa}")
    lipasa = get_val('lipasa')
    if lipasa: labs_parts.append(f"Lipasa {lipasa}")
    if labs_parts:
        objetivo_parts.append("LABORATORIOS: " + ", ".join(labs_parts))
    
    # ===== DISPOSITIVOS INVASIVOS =====
    dispositivos_parts = []
    
    if bool_val(get_val('sonda_urinaria')):
        dias = get_val('dias_sonda_urinaria')
        fec_col = fmt_date(get_val('fecha_colocacion_sonda_urinaria'))
        fec_ret = fmt_date(get_val('fecha_retiro_sonda_urinaria'))
        d = "SONDA URINARIA (Foley)"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('cateter_cvc')):
        dias = get_val('dias_cvc')
        fec_col = fmt_date(get_val('fecha_colocacion_cvc'))
        fec_ret = fmt_date(get_val('fecha_retiro_cvc'))
        d = "CATÉTER VENOSO CENTRAL (CVC)"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocado {fec_col})"
        if fec_ret: d += f" [RETIRADO {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('sonda_endopleural')):
        dias = get_val('dias_endopleural')
        fec_col = fmt_date(get_val('fecha_colocacion_endopleural'))
        fec_ret = fmt_date(get_val('fecha_retiro_endopleural'))
        d = "SONDA ENDOPLEURAL"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('sonda_nasogastrica')):
        dias = get_val('dias_sng')
        fec_col = fmt_date(get_val('fecha_colocacion_sng'))
        fec_ret = fmt_date(get_val('fecha_retiro_sng'))
        d = "SONDA NASOGÁSTRICA (SNG)"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('tubo_endotraqueal')):
        dias = get_val('dias_ett')
        fec_col = fmt_date(get_val('fecha_colocacion_ett'))
        fec_ret = fmt_date(get_val('fecha_retiro_ett'))
        d = "TUBO ENDOTRAQUEAL (ETT)"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocado {fec_col})"
        if fec_ret: d += f" [RETIRADO {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('traqueostomia')):
        dias = get_val('dias_traqueostomia')
        fec_col = fmt_date(get_val('fecha_colocacion_traqueostomia'))
        fec_ret = fmt_date(get_val('fecha_retiro_traqueostomia'))
        d = "TRAQUEOSTOMÍA"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('sonda_lcr')):
        dias = get_val('dias_sonda_lcr')
        fec_col = fmt_date(get_val('fecha_colocacion_lcr'))
        fec_ret = fmt_date(get_val('fecha_retiro_lcr'))
        d = "SONDA DE LCR"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('cateter_intraventricular')):
        dias = get_val('dias_cateter_intraventricular')
        fec_col = fmt_date(get_val('fecha_colocacion_cateter_intraventricular'))
        fec_ret = fmt_date(get_val('fecha_retiro_cateter_intraventricular'))
        d = "CATÉTER INTRAVENTRICULAR"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocado {fec_col})"
        if fec_ret: d += f" [RETIRADO {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('gastrostomia')):
        dias = get_val('dias_gastrostomia')
        fec_col = fmt_date(get_val('fecha_colocacion_gastrostomia'))
        fec_ret = fmt_date(get_val('fecha_retiro_gastrostomia'))
        d = "GASTOSTOMÍA"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    if bool_val(get_val('linea_arterial')):
        dias = get_val('dias_linea_arterial')
        fec_col = fmt_date(get_val('fecha_colocacion_linea_arterial'))
        fec_ret = fmt_date(get_val('fecha_retiro_linea_arterial'))
        d = "LÍNEA ARTERIAL"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocada {fec_col})"
        if fec_ret: d += f" [RETIRADA {fec_ret}]"
        dispositivos_parts.append(d)
    
    # Catéter de hemodiálisis
    if bool_val(get_val('cateter_hemodialisis')):
        dias = get_val('dias_hemodialisis')
        fec_col = fmt_date(get_val('fecha_colocacion_hemodialisis'))
        fec_ret = fmt_date(get_val('fecha_retiro_hemodialisis'))
        d = "CATÉTER DE HEMODIÁLISIS"
        if dias: d += f" - {dias} días"
        if fec_col: d += f" (colocado {fec_col})"
        if fec_ret: d += f" [RETIRADO {fec_ret}]"
        dispositivos_parts.append(d)
    
    if dispositivos_parts:
        objetivo_parts.append("DISPOSITIVOS INVASIVOS:\n" + "\n".join(dispositivos_parts))
    
    # ===== BALANCE HÍDRICO =====
    balance = get_val('balance')
    balance_global = get_val('balance_global')
    indice_urinario = get_val('indice_urinario')
    ingresos = get_val('ingresos')
    egresos = get_val('egresos')
    diuresis = get_val('diuresis')
    drenajes = get_val('drenajes')
    
    balance_parts = []
    if diuresis: balance_parts.append(f"Diuresis: {diuresis} mL")
    if ingresos: balance_parts.append(f"Ingresos: {ingresos} mL")
    if egresos: balance_parts.append(f"Egresos: {egresos} mL")
    if balance: balance_parts.append(f"Balance 24h: {balance} mL")
    if balance_global: balance_parts.append(f"Balance global: {balance_global} mL")
    if indice_urinario: balance_parts.append(f"Índice urinario: {indice_urinario} mL/kg/h")
    if drenajes: balance_parts.append(f"Drenajes: {drenajes}")
    if balance_parts:
        objetivo_parts.append("BALANCE HÍDRICO:\n" + "\n".join(balance_parts))
    
    # ===== IMAGEN / ESTUDIOS / EKG / CULTIVOS =====
    extras_parts = []
    imagen = get_val('imagen_estudios')
    if imagen: extras_parts.append(f"IMAGEN/ESTUDIOS:\n{imagen}")
    ekg = get_val('ekg_texto')
    if ekg: extras_parts.append(f"EKG:\n{ekg}")
    cultivos_resumen = get_val('cultivos_resumen')
    if cultivos_resumen: extras_parts.append(f"CULTIVOS:\n{cultivos_resumen}")
    antibioticos_resumen = get_val('antibioticos_resumen')
    if antibioticos_resumen: extras_parts.append(f"ANTIBIÓTICOS:\n{antibioticos_resumen}")
    extras_texto = "\n\n".join(extras_parts)
    if extras_texto:
        objetivo_parts.append(extras_texto)
    
    # ===== TEXTO LIBRE DEL OBJETIVO =====
    if objetivo_texto and str(objetivo_texto).strip():
        objetivo_parts.append(f"EXPLORACIÓN / NOTAS:\n{objetivo_texto}")
    
    # Construir objetivo completo
    objetivo = '\n\n'.join(objetivo_parts) if objetivo_parts else 'Sin datos objetivos registrados.'
    
    # ===== CÁLCULO DÍAS ESTANCIA =====
    dias_estancia = ""
    fecha_ingreso = patient.get('fecha_ingreso_uci')
    if not fecha_ingreso:
        fecha_ingreso = patient.get('fecha_ingreso')
    if fecha_ingreso:
        try:
            ingreso = datetime.strptime(str(fecha_ingreso)[:10], '%Y-%m-%d')
            hoy = datetime.now()
            dias = (hoy - ingreso).days
            dias_estancia = f"Días de estancia UCI: {dias}"
        except:
            dias_estancia = ""
    
    # ===== DIAGNÓSTICOS =====
    diagnostico_ingreso = patient.get('diagnostico_ingreso', '')
    diagnostico_actual = get_val('diagnostico_actual')
    
    diagnosticos_parts = []
    if diagnostico_ingreso:
        diagnosticos_parts.append(f"Diagnóstico de ingreso: {diagnostico_ingreso}")
    if diagnostico_actual and str(diagnostico_actual).strip():
        diagnosticos_parts.append(f"Diagnósticos actuales: {diagnostico_actual}")
    diagnosticos_texto = "\n".join(diagnosticos_parts) if diagnosticos_parts else ""
    
    # ===== NOTA FINAL =====
    nota = f"""NOTA DE EVOLUCIÓN - PSOAP
Fecha: {fecha} {hora}

PACIENTE: {patient.get('nombre_completo', 'N/A')}
Edad: {patient.get('edad', 'N/A')} años
Sexo: {patient.get('sexo', 'N/A')}
Expediente: {patient.get('expediente', 'N/A')}
CURP: {patient.get('curp', 'N/A')}
Episodio: {patient.get('episodio', 'N/A')}
Cama: {patient.get('cama', 'N/A')}"""
    
    if dias_estancia:
        nota += f"\n{dias_estancia}"
    
    if diagnosticos_texto:
        nota += f"\n\n{diagnosticos_texto}"
    
    # ESCALAS PRONÓSTICAS
    sofa = form_data.get('sofa')
    sofa2 = form_data.get('sofa2')
    apache2 = form_data.get('apache2')
    saps3 = form_data.get('saps3')
    swift = form_data.get('swift')
    
    if any([sofa, sofa2, apache2, saps3, swift]):
        nota += "\n\nESCALAS PRONÓSTICAS:"
        if sofa: nota += f"\n  SOFA: {sofa}"
        if sofa2: nota += f"\n  SOFA2: {sofa2}"
        if apache2: nota += f"\n  APACHE II: {apache2}"
        if saps3: nota += f"\n  SAPS3: {saps3}"
        if swift: nota += f"\n  SWIFT: {swift}"
    
    nota += f"""

═══════════════════════════════════════

S - SUBJETIVO
{subjetivo}

O - OBJETIVO
{objetivo}

A - ANÁLISIS
{analisis}

P - PLAN
{plan}

═══════════════════════════════════════
Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
    
    return nota

def generate_simple_ingreso_note(patient):
    """Genera nota de ingreso simple cuando UCI no está disponible, usando todos los campos disponibles."""
    
    fecha_ingreso = patient.get('fecha_ingreso', date.today().isoformat())
    
    # Campos básicos
    nombre = patient.get('nombre_completo', 'N/A')
    edad = patient.get('edad', 'N/A')
    sexo = patient.get('sexo', 'N/A')
    expediente = patient.get('expediente', 'N/A')
    
    # Signos vitales iniciales
    fc = patient.get('fc', '')
    fr = patient.get('fr', '')
    tas = patient.get('tas', '')
    tad = patient.get('tad', '')
    tam = patient.get('tam', '')
    temp = patient.get('temperatura', '')
    sao2 = patient.get('sao2', '')
    fio2 = patient.get('fio2', '')
    glasgow = patient.get('glasgow', '')
    rass = patient.get('rass', '')
    cpot = patient.get('cpot', '')
    
    # Exploraciones por sistema
    exploracion_parts = []
    if patient.get('exploracion_neurologica'):
        exploracion_parts.append(f"NEUROLÓGICO:\n{patient['exploracion_neurologica']}")
    if patient.get('exploracion_hemodinamica'):
        exploracion_parts.append(f"HEMODINÁMICO:\n{patient['exploracion_hemodinamica']}")
    if patient.get('exploracion_ventilatoria'):
        exploracion_parts.append(f"VENTILATORIO:\n{patient['exploracion_ventilatoria']}")
    if patient.get('exploracion_gastro'):
        exploracion_parts.append(f"GASTROMETABÓLICO:\n{patient['exploracion_gastro']}")
    if patient.get('exploracion_hema'):
        exploracion_parts.append(f"HEMATOLÓGICO/INFECCIOSO:\n{patient['exploracion_hema']}")
    
    exploracion_completa = '\n\n'.join(exploracion_parts) if exploracion_parts else 'No se registró exploración física detallada.'
    
    # Ventilación
    vent_parts = []
    modo = patient.get('modo_ventilatorio', '')
    if modo:
        vent_parts.append(f"Modo: {modo}")
        if patient.get('vt_psinp'): vent_parts.append(f"VT/PS: {patient['vt_psinp']}")
        if patient.get('peep'): vent_parts.append(f"PEEP: {patient['peep']} cmH2O")
        if patient.get('ppico'): vent_parts.append(f"Ppico: {patient['ppico']} cmH2O")
        if patient.get('pplat'): vent_parts.append(f"Pplat: {patient['pplat']} cmH2O")
        if patient.get('driving_pressure'): vent_parts.append(f"Driving P: {patient['driving_pressure']} cmH2O")
        if patient.get('nif'): vent_parts.append(f"NIF: {patient['nif']} cmH2O")
        if patient.get('p0_1'): vent_parts.append(f"P0.1: {patient['p0_1']} cmH2O")
        if patient.get('pafi'): vent_parts.append(f"PaFi: {patient['pafi']} mmHg")
        if patient.get('tobin'): vent_parts.append(f"Tobin: {patient['tobin']}")
    
    # Gasometría
    gaso_parts = []
    if patient.get('gasometria_ph'): gaso_parts.append(f"pH: {patient['gasometria_ph']}")
    if patient.get('gasometria_pco2'): gaso_parts.append(f"pCO2: {patient['gasometria_pco2']} mmHg")
    if patient.get('gasometria_po2'): gaso_parts.append(f"pO2: {patient['gasometria_po2']} mmHg")
    if patient.get('gasometria_hco3'): gaso_parts.append(f"HCO3: {patient['gasometria_hco3']} mEq/L")
    if patient.get('gasometria_lactato'): gaso_parts.append(f"Lactato: {patient['gasometria_lactato']} mmol/L")
    
    # Laboratorios
    labs = []
    if patient.get('hemoglobina'): labs.append(f"Hb: {patient['hemoglobina']} g/dL")
    if patient.get('hematocrito'): labs.append(f"Hto: {patient['hematocrito']} %")
    if patient.get('leucocitos'): labs.append(f"Leu: {patient['leucocitos']}")
    if patient.get('neutrofilos'): labs.append(f"Neutrofilos: {patient['neutrofilos']} %")
    if patient.get('linfocitos'): labs.append(f"Linfocitos: {patient['linfocitos']} %")
    if patient.get('plaquetas'): labs.append(f"Plaq: {patient['plaquetas']}")
    if patient.get('pcr'): labs.append(f"PCR: {patient['pcr']} mg/L")
    if patient.get('pct'): labs.append(f"PCT: {patient['pct']} ng/mL")
    if patient.get('vsg'): labs.append(f"VSG: {patient['vsg']} mm/h")
    if patient.get('creatinina'): labs.append(f"Creat: {patient['creatinina']} mg/dL")
    if patient.get('bun'): labs.append(f"BUN: {patient['bun']} mg/dL")
    if patient.get('urea'): labs.append(f"Urea: {patient['urea']} mg/dL")
    if patient.get('sodio'): labs.append(f"Na: {patient['sodio']} mEq/L")
    if patient.get('potasio'): labs.append(f"K: {patient['potasio']} mEq/L")
    if patient.get('cloro'): labs.append(f"Cl: {patient['cloro']} mEq/L")
    if patient.get('calcio'): labs.append(f"Ca: {patient['calcio']} mg/dL")
    if patient.get('magnesio'): labs.append(f"Mg: {patient['magnesio']} mg/dL")
    if patient.get('fosforo'): labs.append(f"P: {patient['fosforo']} mg/dL")
    if patient.get('glucosa_central'): labs.append(f"Gluc: {patient['glucosa_central']} mg/dL")
    if patient.get('albumina'): labs.append(f"Alb: {patient['albumina']} g/dL")
    if patient.get('bilirrubina_total'): labs.append(f"Bili T: {patient['bilirrubina_total']} mg/dL")
    if patient.get('bilirrubina_directa'): labs.append(f"Bili D: {patient['bilirrubina_directa']} mg/dL")
    if patient.get('bilirrubina_indirecta'): labs.append(f"Bili I: {patient['bilirrubina_indirecta']} mg/dL")
    if patient.get('ast'): labs.append(f"AST: {patient['ast']} U/L")
    if patient.get('alt'): labs.append(f"ALT: {patient['alt']} U/L")
    if patient.get('dhl'): labs.append(f"DHL: {patient['dhl']} U/L")
    if patient.get('fosfatasa_alcalina'): labs.append(f"FA: {patient['fosfatasa_alcalina']} U/L")
    if patient.get('amilasa'): labs.append(f"Amilasa: {patient['amilasa']} U/L")
    if patient.get('lipasa'): labs.append(f"Lipasa: {patient['lipasa']} U/L")
    if patient.get('troponina'): labs.append(f"Troponina: {patient['troponina']} ng/L")
    if patient.get('bnp'): labs.append(f"BNP: {patient['bnp']} pg/mL")
    if patient.get('dimero_d'): labs.append(f"D-Dimero: {patient['dimero_d']} ng/mL")
    if patient.get('tp'): labs.append(f"TP: {patient['tp']} seg")
    if patient.get('ttp'): labs.append(f"TTP: {patient['ttp']} seg")
    if patient.get('inr'): labs.append(f"INR: {patient['inr']}")
    if patient.get('fibrinogeno'): labs.append(f"Fibrinógeno: {patient['fibrinogeno']} mg/dL")
    
    # Balance
    balance_parts = []
    if patient.get('ingresos'): balance_parts.append(f"Ingresos: {patient['ingresos']} mL")
    if patient.get('egresos'): balance_parts.append(f"Egresos: {patient['egresos']} mL")
    if patient.get('diuresis_total'): balance_parts.append(f"Diuresis: {patient['diuresis_total']} mL")
    if patient.get('balance'): balance_parts.append(f"Balance: {patient['balance']} mL")
    if patient.get('balance_global'): balance_parts.append(f"Balance global: {patient['balance_global']} mL")
    if patient.get('indice_urinario'): balance_parts.append(f"Índice urinario: {patient['indice_urinario']}")
    
    # Escores
    scores = []
    if patient.get('news2_ingreso'): scores.append(f"NEWS2: {patient['news2_ingreso']} - {patient.get('news2_interpretado', '')}")
    if patient.get('sofa_ingreso'): scores.append(f"SOFA: {patient['sofa_ingreso']} (Mortalidad estimada: {patient.get('sofa_mortalidad', '')})")
    if patient.get('apache2_ingreso'): scores.append(f"APACHE II: {patient['apache2_ingreso']} (Mortalidad: {patient.get('apache2_mortalidad', '')})")
    if patient.get('saps3_ingreso'): scores.append(f"SAPS 3: {patient['saps3_ingreso']} (Mortalidad: {patient.get('saps3_mortalidad', '')})")
    if patient.get('swift_score'): scores.append(f"SWIFT: {patient['swift_score']}")
    
    # EKG
    ekg_text = patient.get('ekg', '')
    
    # Construir nota
    nota = f"""NOTA DE INGRESO UCI

Paciente: {nombre}
Edad: {edad} años, Sexo: {sexo}
Expediente: {expediente}
Fecha de ingreso: {fecha_ingreso}
"""
    
    if patient.get('procedencia'):
        nota += f"Procedencia: {patient['procedencia']}\n"
    if patient.get('servicio_tratante'):
        nota += f"Servicio tratante: {patient['servicio_tratante']}\n"
    if patient.get('cama'):
        nota += f"Cama: {patient['cama']}\n"
    
    nota += f"""
DIAGNÓSTICO DE INGRESO:
{patient.get('diagnostico_ingreso', 'No especificado')}

"""
    
    # Signos vitales
    if any([fc, fr, tas, tad, temp, glasgow]):
        nota += "SIGNOS VITALES INICIALES:\n"
        if fc: nota += f"FC: {fc} lpm\n"
        if fr: nota += f"FR: {fr} rpm\n"
        if tas: nota += f"TAS: {tas} mmHg\n"
        if tad: nota += f"TAD: {tad} mmHg\n"
        if tam: nota += f"TAM: {tam} mmHg\n"
        if temp: nota += f"Temp: {temp} °C\n"
        if sao2: nota += f"SpO2: {sao2}"
        if fio2: nota += f" (FiO2: {fio2}%)"
        if sao2 or fio2: nota += "\n"
        if glasgow: nota += f"Glasgow: {glasgow}/15\n"
        if rass: nota += f"RASS: {rass}\n"
        if cpot: nota += f"CPOT: {cpot}\n"
        nota += "\n"
    
    # Escores
    if scores:
        nota += "ESCORES DE SEVERIDAD:\n* " + "\n* ".join(scores) + "\n\n"
    
    # EKG
    if ekg_text:
        nota += f"ELECTROCARDIOGRAMA:\n{ekg_text}\n\n"
    
    # Ventilación
    if vent_parts:
        nota += "SOPORTE VENTILATORIO:\n* " + "\n* ".join(vent_parts) + "\n\n"
    
    # Gasometría
    if gaso_parts:
        nota += "GASOMETRÍA:\n* " + "\n* ".join(gaso_parts) + "\n\n"
    
    # Laboratorios
    if labs:
        nota += "LABORATORIOS INICIALES:\n* " + "\n* ".join(labs) + "\n\n"
    
    # Balance
    if balance_parts:
        nota += "BALANCE HÍDRICO:\n* " + "\n* ".join(balance_parts) + "\n\n"
    
    # Exploración física
    nota += f"""EXPLORACIÓN FÍSICA POR APARATOS Y SISTEMAS:
{exploracion_completa}

"""
    
    # Plan
    nota += f"""PLAN INICIAL:
{patient.get('plan_ingreso', '1. Monitoreo continuo\n2. Manejo según protocolo')}

─────────────────────────────────
Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
    
    return nota


def generate_egreso_note(patient):
    """Genera nota de egreso del paciente con todos los datos disponibles."""
    
    fecha_egreso = patient.get('fecha_egreso_uci', date.today().isoformat())
    fecha_egreso_hosp = patient.get('fecha_egreso_hospital', '')
    fecha_ingreso = patient.get('fecha_ingreso', 'N/A')
    fecha_ingreso_hosp = patient.get('fecha_ingreso_hosp', '')
    
    # Calcular días de estancia
    dias_uci = ''
    dias_hosp = ''
    if fecha_ingreso and fecha_ingreso != 'N/A':
        try:
            ing = datetime.strptime(str(fecha_ingreso), '%Y-%m-%d').date()
            egr = datetime.strptime(str(fecha_egreso), '%Y-%m-%d').date()
            dias_uci = (egr - ing).days
        except:
            pass
    
    if fecha_ingreso_hosp and fecha_egreso_hosp:
        try:
            ing_h = datetime.strptime(str(fecha_ingreso_hosp), '%Y-%m-%d').date()
            egr_h = datetime.strptime(str(fecha_egreso_hosp), '%Y-%m-%d').date()
            dias_hosp = (egr_h - ing_h).days
        except:
            pass
    
    # Construir secciones con datos completos
    dx_ingreso = patient.get('diagnostico_ingreso', '')
    dx_egreso = patient.get('diagnostico_egreso', '')
    
    # Signos vitales de egreso
    fc_e = patient.get('fc_egreso', '')
    fr_e = patient.get('fr_egreso', '')
    tas_e = patient.get('tas_egreso', '')
    tad_e = patient.get('tad_egreso', '')
    tam_e = patient.get('tam_egreso', '')
    temp_e = patient.get('temperatura_egreso', '')
    sao2_e = patient.get('sao2_egreso', '')
    fio2_e = patient.get('fio2_egreso', '')
    pafi_e = patient.get('pafi_egreso', '')
    
    # Labs de egreso
    labs_egreso = []
    if patient.get('hemoglobina_egreso'): labs_egreso.append(f"Hb: {patient['hemoglobina_egreso']} g/dL")
    if patient.get('hematocrito_egreso'): labs_egreso.append(f"Hto: {patient['hematocrito_egreso']} %")
    if patient.get('leucocitos_egreso'): labs_egreso.append(f"Leu: {patient['leucocitos_egreso']}")
    if patient.get('neutrofilos_egreso'): labs_egreso.append(f"Neutrofilos: {patient['neutrofilos_egreso']} %")
    if patient.get('linfocitos_egreso'): labs_egreso.append(f"Linfocitos: {patient['linfocitos_egreso']} %")
    if patient.get('plaquetas_egreso'): labs_egreso.append(f"Plaq: {patient['plaquetas_egreso']}")
    if patient.get('pcr_egreso'): labs_egreso.append(f"PCR: {patient['pcr_egreso']} mg/L")
    if patient.get('pct_egreso'): labs_egreso.append(f"PCT: {patient['pct_egreso']} ng/mL")
    if patient.get('sodio_egreso'): labs_egreso.append(f"Na: {patient['sodio_egreso']} mEq/L")
    if patient.get('potasio_egreso'): labs_egreso.append(f"K: {patient['potasio_egreso']} mEq/L")
    if patient.get('cloro_egreso'): labs_egreso.append(f"Cl: {patient['cloro_egreso']} mEq/L")
    if patient.get('creatinina_egreso'): labs_egreso.append(f"Creat: {patient['creatinina_egreso']} mg/dL")
    if patient.get('bun_egreso'): labs_egreso.append(f"BUN: {patient['bun_egreso']} mg/dL")
    if patient.get('urea_egreso'): labs_egreso.append(f"Urea: {patient['urea_egreso']} mg/dL")
    if patient.get('glucosa_egreso'): labs_egreso.append(f"Gluc: {patient['glucosa_egreso']} mg/dL")
    if patient.get('bilirrubina_total_egreso'): labs_egreso.append(f"Bili T: {patient['bilirrubina_total_egreso']} mg/dL")
    if patient.get('bilirrubina_directa_egreso'): labs_egreso.append(f"Bili D: {patient['bilirrubina_directa_egreso']} mg/dL")
    if patient.get('albumina_egreso'): labs_egreso.append(f"Alb: {patient['albumina_egreso']} g/dL")
    if patient.get('gasometria_ph_egreso'): labs_egreso.append(f"pH: {patient['gasometria_ph_egreso']}")
    if patient.get('gasometria_pco2_egreso'): labs_egreso.append(f"pCO2: {patient['gasometria_pco2_egreso']} mmHg")
    if patient.get('gasometria_po2_egreso'): labs_egreso.append(f"pO2: {patient['gasometria_po2_egreso']} mmHg")
    if patient.get('gasometria_hco3_egreso'): labs_egreso.append(f"HCO3: {patient['gasometria_hco3_egreso']} mEq/L")
    if patient.get('gasometria_lactato_egreso'): labs_egreso.append(f"Lactato: {patient['gasometria_lactato_egreso']} mmol/L")
    
    # Escores de egreso
    scores_egreso = []
    if patient.get('news2_egreso'): scores_egreso.append(f"NEWS2: {patient['news2_egreso']}")
    if patient.get('sofa_egreso'): scores_egreso.append(f"SOFA: {patient['sofa_egreso']}")
    if patient.get('sofa2_egreso'): scores_egreso.append(f"SOFA2: {patient['sofa2_egreso']}")
    if patient.get('apache2_egreso'): scores_egreso.append(f"APACHE II: {patient['apache2_egreso']}")
    if patient.get('saps_egreso'): scores_egreso.append(f"SAPS: {patient['saps_egreso']}")
    
    # Fechas de procedimientos
    fechas_proc = []
    if patient.get('fecha_extubacion'): fechas_proc.append(f"Extubación: {patient['fecha_extubacion']}")
    if patient.get('fecha_retiro_cvc'): fechas_proc.append(f"Retiro CVC: {patient['fecha_retiro_cvc']}")
    if patient.get('fecha_retiro_sonda_urinaria'): fechas_proc.append(f"Retiro sonda urinaria: {patient['fecha_retiro_sonda_urinaria']}")
    if patient.get('fecha_defuncion'): fechas_proc.append(f"Defunción: {patient['fecha_defuncion']}")
    
    # Campos adicionales de egreso (v2)
    dias_vm = patient.get('dias_ventilacion_mecanica', '')
    dias_sonda = patient.get('dias_sonda_urinaria_egreso', '')
    infeccion_hai = patient.get('infeccion_hai', '')
    hai_tipo = patient.get('hai_tipo', '')
    lesion_renal = patient.get('lesion_renal_aguda', '')
    evento_quir = patient.get('evento_quirurgico_estancia', '')
    reingreso = patient.get('es_reingreso', '')
    muerte_encefalica = patient.get('muerte_encefalica', '')
    diagnostico_codificado = patient.get('diagnostico_codificado', '')
    
    # Construir nota completa
    nota = f"""NOTA DE EGRESO UCI

Paciente: {patient.get('nombre_completo', 'N/A')}
Edad: {patient.get('edad', 'N/A')} años, Sexo: {patient.get('sexo', 'N/A')}
Expediente: {patient.get('expediente', 'N/A')}

INGRESO: {fecha_ingreso}
EGRESO UCI: {fecha_egreso}
"""
    
    if dias_uci:
        nota += f"DÍAS DE ESTANCIA UCI: {dias_uci}\n"
    if fecha_ingreso_hosp and fecha_egreso_hosp:
        nota += f"DÍAS DE ESTANCIA HOSPITALARIA: {dias_hosp if dias_hosp else 'N/A'}\n"
    
    nota += f"""
CONDICIÓN DE EGRESO: {patient.get('condicion_egreso', 'No especificada')}
DESTINO: {patient.get('destino_egreso', 'No especificado')}
TIPO DE EGRESO: {patient.get('tipo_egreso', 'No especificado')}
SERVICIO DE EGRESO: {patient.get('servicio_egreso', 'No especificado')}

DIAGNÓSTICO DE INGRESO:
{dx_ingreso if dx_ingreso else 'No especificado'}

DIAGNÓSTICO DE EGRESO:
{dx_egreso if dx_egreso else 'No especificado'}

"""
    
    # Signos vitales al egreso
    if any([fc_e, fr_e, tas_e, tad_e]):
        nota += "SIGNOS VITALES AL EGRESO:\n"
        if fc_e: nota += f"FC: {fc_e} lpm\n"
        if fr_e: nota += f"FR: {fr_e} rpm\n"
        if tas_e: nota += f"TAS: {tas_e} mmHg\n"
        if tad_e: nota += f"TAD: {tad_e} mmHg\n"
        if tam_e: nota += f"TAM: {tam_e} mmHg\n"
        if temp_e: nota += f"Temp: {temp_e} °C\n"
        if sao2_e: nota += f"SpO2: {sao2_e}%\n"
        if fio2_e: nota += f"FiO2: {fio2_e}%\n"
        if pafi_e: nota += f"PaFi: {pafi_e} mmHg\n"
        nota += "\n"
    
    # Laboratorios al egreso
    if labs_egreso:
        nota += "LABORATORIOS AL EGRESO:\n* " + "\n* ".join(labs_egreso) + "\n\n"
    
    # Escores
    if scores_egreso:
        nota += "ESCORES AL EGRESO:\n* " + "\n* ".join(scores_egreso) + "\n\n"
    
    # Procedimientos
    if fechas_proc:
        nota += "FECHAS DE PROCEDIMIENTOS/EVENTOS:\n* " + "\n* ".join(fechas_proc) + "\n\n"
    
    # Campos adicionales de egreso (v2)
    campos_adicionales = []
    if dias_vm: campos_adicionales.append(f"Días de Ventilación Mecánica: {dias_vm}")
    if dias_sonda: campos_adicionales.append(f"Días de Sonda Urinaria: {dias_sonda}")
    if infeccion_hai == 'Sí':
        hai_text = "Infección HAI: Sí"
        if hai_tipo: hai_text += f" ({hai_tipo})"
        campos_adicionales.append(hai_text)
    elif infeccion_hai == 'No':
        campos_adicionales.append("Infección HAI: No")
    if lesion_renal: campos_adicionales.append(f"Lesión Renal Aguda: {lesion_renal}")
    if evento_quir: campos_adicionales.append(f"Evento Quirúrgico durante Estancia: {evento_quir}")
    if reingreso: campos_adicionales.append(f"Es Reingreso: {reingreso}")
    if muerte_encefalica: campos_adicionales.append(f"Muerte Encefálica: {muerte_encefalica}")
    if diagnostico_codificado: campos_adicionales.append(f"Diagnóstico Codificado: {diagnostico_codificado}")
    
    if campos_adicionales:
        nota += "DATOS ADICIONALES DE ESTANCIA:\n* " + "\n* ".join(campos_adicionales) + "\n\n"
    
    # Plan al egreso
    nota += f"""PLAN AL EGRESO:
{patient.get('plan_egreso', 'Seguimiento ambulatorio')}

─────────────────────────────────
Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
    
    return nota


def generate_raw_note(patient, patient_id):
    """Genera un dump de todos los datos del paciente."""
    
    lines = ["=" * 60]
    lines.append("RAW DUMP - DATOS COMPLETOS DEL PACIENTE")
    lines.append("=" * 60)
    lines.append(f"ID: {patient_id}")
    lines.append(f"Nombre: {patient.get('nombre_completo', 'N/A')}")
    lines.append(f"Expediente: {patient.get('expediente', 'N/A')}")
    lines.append(f"CURP: {patient.get('curp', 'N/A')}")
    lines.append(f"Fecha de ingreso: {patient.get('fecha_ingreso', 'N/A')}")
    lines.append("")
    
    # Datos completos del paciente
    lines.append("-" * 60)
    lines.append("DATOS DEL INGRESO:")
    lines.append("-" * 60)
    
    for key, value in sorted(patient.items()):
        if value is not None and value != '':
            lines.append(f"{key}: {value}")
    
    # Evoluciones
    lines.append("")
    lines.append("=" * 60)
    lines.append("EVOLUCIONES:")
    lines.append("=" * 60)
    
    try:
        evoluciones = get_evolutions(patient_id)
        if evoluciones:
            for evo in evoluciones:
                lines.append("")
                lines.append(f"--- Evolución ID: {evo.get('id', 'N/A')} ---")
                lines.append(f"Fecha: {evo.get('fecha', 'N/A')} {evo.get('hora', '')}")
                for key, value in sorted(evo.items()):
                    if value is not None and value != '' and key not in ['id', 'patient_id', 'created_at']:
                        lines.append(f"  {key}: {value}")
        else:
            lines.append("Sin evoluciones registradas.")
    except Exception as e:
        lines.append(f"Error obteniendo evoluciones: {e}")
    
    # TABLAS DINÁMICAS
    lines.append("")
    lines.append("=" * 60)
    lines.append("TABLAS DINÁMICAS:")
    lines.append("=" * 60)
    
    try:
        tablas_nombres = [
            'medicamentos_neurologicos', 'medicamentos_hemodinamicos',
            'medicamentos_nefro', 'medicamentos_gastro',
            'medicacion_hematologica', 'cultivos', 'transfusiones'
        ]
        for tabla in tablas_nombres:
            items = get_dynamic_items(tabla, patient_id)
            if items:
                lines.append("")
                lines.append(f"--- {tabla.upper().replace('_', ' ')} ---")
                for item in items:
                    lines.append(f"  ID {item.get('id')}:")
                    for k, v in sorted(item.items()):
                        if v is not None and v != '' and k not in ['id', 'patient_id', 'created_at']:
                            lines.append(f"    {k}: {v}")
    except Exception as e:
        lines.append(f"Error obteniendo tablas dinámicas: {e}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    lines.append("=" * 60)
    
    return '\n'.join(lines)


@app.route('/api/medications', methods=['GET'])
@login_required
def api_medications():
    """Get medications dictionary."""
    medications_file = os.path.join(app.static_folder, 'data', 'medications.json')
    
    try:
        with open(medications_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        category = request.args.get('category')
        if category and category in data:
            return jsonify({'success': True, 'category': category, 'data': data[category]})
        
        return jsonify({'success': True, 'categories': list(data.keys()), 'data': data})
    except FileNotFoundError:
        return jsonify({'error': 'Archivo de medicamentos no encontrado'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Error al parsear medicamentos'}), 500


@app.route('/library')
@login_required
def library():
    """Biblioteca médica - muestra artículos de investigación."""
    query = request.args.get('q', '').strip()
    
    if query:
        articles = search_articles(query, limit=20)
    else:
        articles = get_all_articles(limit=20)
    
    featured = get_featured_article()
    stats = get_library_stats()
    
    return render_template('library.html',
                         articles=articles,
                         featured_article=featured,
                         stats=stats,
                         query=query)


@app.route('/library/article/<article_id>')
@login_required
def library_article(article_id):
    """Ver artículo individual."""
    article = get_article(article_id)
    
    if not article:
        flash('Artículo no encontrado', 'error')
        return redirect(url_for('library'))
    
    return render_template('article_view.html', article=article)


# ============================================================================
# API - Generar Nota PSOAP (servidor-side)
# ============================================================================


@app.route('/api/generate-psoas-note', methods=['POST'])
@login_required
def api_generate_psoas_note():
    """Genera nota PSOAP v2 usando todos los campos del formulario."""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        patient = get_patient(patient_id) if patient_id else None
        form_data = data.get('form_data', {})
        
        # Asegurar que form_data sea un dict
        if isinstance(form_data, str):
            import json
            try:
                form_data = json.loads(form_data)
            except:
                form_data = {}
        
        # Generar la nota usando la funcion v2
        nota = generar_nota_psoap_dump(patient, form_data, patient_id)
        
        return jsonify({
            'success': True,
            'note': nota
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': tb
        }), 500


@app.route('/api/generate-ingreso-note', methods=['POST'])
@login_required
def api_generate_ingreso_note():
    """Genera nota de ingreso UCI usando el generador avanzado del Dr. Pablo."""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return jsonify({'success': False, 'error': 'Se requiere patient_id'}), 400
        
        patient = get_patient(patient_id)
        if not patient:
            return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404
        
        # Obtener más datos del paciente para el generador
        patient_data = {
            'id': patient_id,
            'nombre_completo': patient.get('nombre_completo', ''),
            'edad': patient.get('edad', ''),
            'sexo': patient.get('sexo', ''),
            'expediente': patient.get('expediente', ''),
            'fecha_ingreso': patient.get('fecha_ingreso', ''),
            'diagnostico_ingreso': patient.get('diagnostico_ingreso', ''),
            'plan_ingreso': patient.get('plan_ingreso', ''),
            'procedencia': patient.get('procedencia', ''),
            'servicio_tratante': patient.get('servicio_tratante', ''),
            'cama': patient.get('cama', ''),
            # Signos vitales iniciales
            'fc': patient.get('fc', ''),
            'fr': patient.get('fr', ''),
            'tas': patient.get('tas', ''),
            'tad': patient.get('tad', ''),
            'tam': patient.get('tam', ''),
            'temperatura': patient.get('temperatura', ''),
            'sao2': patient.get('sao2', ''),
            'fio2': patient.get('fio2', ''),
            'glasgow': patient.get('glasgow', ''),
            'rass': patient.get('rass', ''),
            'cpot': patient.get('cpot', ''),
            # Exploraciones
            'exploracion_neurologica': patient.get('exploracion_neurologica', ''),
            'exploracion_hemodinamica': patient.get('exploracion_hemodinamica', ''),
            'exploracion_ventilatoria': patient.get('exploracion_ventilatoria', ''),
            'exploracion_gastro': patient.get('exploracion_gastro', ''),
            'exploracion_hema': patient.get('exploracion_hema', ''),
            # Ventilación
            'modo_ventilatorio': patient.get('modo_ventilatorio', ''),
            'vt_psinp': patient.get('vt_psinp', ''),
            'peep': patient.get('peep', ''),
            'ppico': patient.get('ppico', ''),
            'pplat': patient.get('pplat', ''),
            'driving_pressure': patient.get('driving_pressure', ''),
            'nif': patient.get('nif', ''),
            'p0_1': patient.get('p0_1', ''),
            'pafi': patient.get('pafi', ''),
            'tobin': patient.get('tobin', ''),
            # Gasometría
            'gasometria_ph': patient.get('gasometria_ph', ''),
            'gasometria_pco2': patient.get('gasometria_pco2', ''),
            'gasometria_po2': patient.get('gasometria_po2', ''),
            'gasometria_hco3': patient.get('gasometria_hco3', ''),
            'gasometria_lactato': patient.get('gasometria_lactato', ''),
            # Laboratorios
            'hemoglobina': patient.get('hemoglobina', ''),
            'hematocrito': patient.get('hematocrito', ''),
            'leucocitos': patient.get('leucocitos', ''),
            'neutrofilos': patient.get('neutrofilos', ''),
            'linfocitos': patient.get('linfocitos', ''),
            'plaquetas': patient.get('plaquetas', ''),
            'pcr': patient.get('pcr', ''),
            'pct': patient.get('pct', ''),
            'vsg': patient.get('vsg', ''),
            'creatinina': patient.get('creatinina', ''),
            'bun': patient.get('bun', ''),
            'urea': patient.get('urea', ''),
            'sodio': patient.get('sodio', ''),
            'potasio': patient.get('potasio', ''),
            'cloro': patient.get('cloro', ''),
            'calcio': patient.get('calcio', ''),
            'magnesio': patient.get('magnesio', ''),
            'fosforo': patient.get('fosforo', ''),
            'glucosa_central': patient.get('glucosa_central', ''),
            'albumina': patient.get('albumina', ''),
            'bilirrubina_total': patient.get('bilirrubina_total', ''),
            'bilirrubina_directa': patient.get('bilirrubina_directa', ''),
            'bilirrubina_indirecta': patient.get('bilirrubina_indirecta', ''),
            'ast': patient.get('ast', ''),
            'alt': patient.get('alt', ''),
            'dhl': patient.get('dhl', ''),
            'fosfatasa_alcalina': patient.get('fosfatasa_alcalina', ''),
            'amilasa': patient.get('amilasa', ''),
            'lipasa': patient.get('lipasa', ''),
            'troponina': patient.get('troponina', ''),
            'bnp': patient.get('bnp', ''),
            'dimero_d': patient.get('dimero_d', ''),
            'tp': patient.get('tp', ''),
            'ttp': patient.get('ttp', ''),
            'inr': patient.get('inr', ''),
            'fibrinogeno': patient.get('fibrinogeno', ''),
            # Balance
            'ingresos': patient.get('ingresos', ''),
            'egresos': patient.get('egresos', ''),
            'balance': patient.get('balance', ''),
            'balance_global': patient.get('balance_global', ''),
            'diuresis_total': patient.get('diuresis_total', ''),
            'indice_urinario': patient.get('indice_urinario', ''),
            # Escores
            'news2_ingreso': patient.get('news2_ingreso', ''),
            'news2_interpretado': patient.get('news2_interpretado', ''),
            'sofa_ingreso': patient.get('sofa_ingreso', ''),
            'sofa_mortalidad': patient.get('sofa_mortalidad', ''),
            'apache2_ingreso': patient.get('apache2_ingreso', ''),
            'apache2_mortalidad': patient.get('apache2_mortalidad', ''),
            'saps3_ingreso': patient.get('saps3_ingreso', ''),
            'saps3_mortalidad': patient.get('saps3_mortalidad', ''),
            'swift_score': patient.get('swift_score', ''),
            # Nutrición
            'tipo_nutricion': patient.get('tipo_nutricion', ''),
            'producto_nutricion': patient.get('producto_nutricion', ''),
            'volumen_aporte': patient.get('volumen_aporte', ''),
            'kcal_aporte': patient.get('kcal_aporte', ''),
            'proteinas_aporte': patient.get('proteinas_aporte', ''),
            # Campos adicionales
            'ekg': patient.get('ekg', ''),
            'drenajes': patient.get('drenajes', ''),
            'sonda_vesical': patient.get('sonda_vesical', ''),
            'sonda_levin': patient.get('sonda_levin', ''),
            'traqueostomia_ingreso': patient.get('traqueostomia_ingreso', ''),
            'numero_tubo': patient.get('numero_tubo', ''),
            'gastrostomia_ingreso': patient.get('gastrostomia_ingreso', ''),
            'peso_estimado': patient.get('peso_estimado', ''),
            'talla': patient.get('talla', ''),
            'peso_ideal': patient.get('peso_ideal', ''),
            'imc': patient.get('imc', ''),
        }
        
        if not uci_note_disponible():
            return jsonify({
                'success': False, 
                'error': 'Generador UCI no disponible. Verificar skill notas-uci-assistant.'
            }), 503
        
        # Obtener última evolución si existe para enriquecer datos
        evoluciones = get_evolutions(patient_id, limit=1)
        evolution_data = evoluciones[0] if evoluciones else None
        
        # Generar nota con todos los datos
        nota = generar_nota_ingreso_uci(patient_data, evolution_data)
        
        # Si el skill genera nota vacía o muy corta, usar generador simple local
        if nota.startswith('ERROR') or len(nota) < 500:
            print(f"Skill generó nota corta ({len(nota)} chars), usando generador simple local")
            nota = generate_simple_ingreso_note(patient_data)
            generator_used = 'simple_local'
        else:
            generator_used = 'notas-uci-assistant'
        
        return jsonify({
            'success': True,
            'note': nota,
            'template': 'nota_ingreso_uci_avanzada',
            'generator': generator_used
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================


@app.route('/api/generate-egreso-note', methods=['POST'])
@login_required
def api_generate_egreso_note():
    """Genera nota de egreso UCI usando el generador completo del Dr. Pablo."""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return jsonify({'success': False, 'error': 'Se requiere patient_id'}), 400
        
        patient = get_patient(patient_id)
        if not patient:
            return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404
        
        form_data = data.get('form_data', {})
        if isinstance(form_data, str):
            try:
                form_data = json.loads(form_data)
            except:
                form_data = {}
        
        # Generar nota de egreso
        nota = generar_nota_egreso(patient, form_data, patient_id)
        
        return jsonify({
            'success': True,
            'note': nota
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
# GENERADOR DE NOTAS UNIFICADO
# IMPORTAR - Sistema de importación de datos clínicos (v2 con confirmación)
# ============================================================================

@app.route('/import', methods=['GET'])
@login_required
def import_page():
    """Página de importación de datos clínicos."""
    # Ejemplo de texto para importación (datos ficticios de demostración)
    texto_ejemplo = """PACIENTE: [NOMBRE ANONIMIZADO]
EDAD: [EDAD] años

Texto clínico de ejemplo para demostración del sistema de importación.
"""
    
    return render_template('import.html', texto_ejemplo=texto_ejemplo)


@app.route('/api/import/analyze', methods=['POST'])
@login_required
def api_import_analyze():
    """
    Paso 1: Solo analiza el texto, extrae campos, busca paciente.
    NO modifica la base de datos.
    """
    logger.debug("api_import_analyze: INICIO")
    try:
        data = request.get_json() or {}
        texto = data.get('texto', '').strip()
        tipo = data.get('tipo', 'nota_evolucion')
        logger.debug(f"api_import_analyze: texto_len={len(texto)}, tipo={tipo}")
        
        if not texto:
            return jsonify({'success': False, 'error': 'No se proporcionó texto'}), 400
        
        resultado = {
            'success': True,
            'tipo': tipo,
            'datos_extraidos': {}
        }
        
        # Extraer datos del texto
        logger.debug("api_import_analyze: llamando extraer_datos_clinicos...")
        datos_extraidos = extraer_datos_clinicos(texto, tipo)
        logger.debug(f"api_import_analyze: datos_extraidos={datos_extraidos}")
        resultado['datos_extraidos'] = datos_extraidos
        resultado['campos_count'] = len([v for v in datos_extraidos.values() if v is not None and v != ''])
        
        # Buscar paciente (solo consulta, no modifica)
        logger.debug("api_import_analyze: buscando paciente...")
        nombre = datos_extraidos.get('nombre_completo', '')
        expediente = datos_extraidos.get('expediente', '')
        paciente_encontrado = None
        
        if expediente:
            logger.debug(f"api_import_analyze: buscando por expediente={expediente}")
            paciente_encontrado = get_patient_by_expediente(expediente)
            logger.debug(f"api_import_analyze: paciente_encontrado={paciente_encontrado is not None}")
        
        if not paciente_encontrado and nombre:
            logger.debug(f"api_import_analyze: buscando por nombre={nombre}")
            pacientes = get_all_patients(status='ingreso')
            for p in pacientes:
                if nombre.lower() in (p.get('nombre_completo') or '').lower() or \
                   (p.get('nombre_completo') or '').lower() in nombre.lower():
                    paciente_encontrado = p
                    break
            logger.debug(f"api_import_analyze: pacientes_iterados={len(pacientes)}")
        
        if paciente_encontrado:
            resultado['paciente_existente'] = {
                'id': paciente_encontrado['id'],
                'nombre_completo': paciente_encontrado.get('nombre_completo', ''),
                'expediente': paciente_encontrado.get('expediente', ''),
                'edad': paciente_encontrado.get('edad', ''),
                'sexo': paciente_encontrado.get('sexo', ''),
                'diagnostico_ingreso': paciente_encontrado.get('diagnostico_ingreso', '')
            }
        else:
            resultado['paciente_existente'] = None
        
        logger.debug("api_import_analyze: RETORNANDO OK")
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR en api_import_analyze: {error_msg}")
        print(error_trace)
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': error_trace
        }), 500


@app.route('/api/import/execute', methods=['POST'])
@login_required
def api_import_execute():
    """
    Ejecuta los cambios. Recibe datos ya parseados del frontend.
    Busca paciente por nombre/expediente, crea si no existe (solo historia_clinica).
    """
    try:
        data = request.get_json() or {}
        datos = data.get('datos', {})
        tipo = data.get('tipo', 'nota_evolucion')
        
        if not datos:
            return jsonify({'success': False, 'error': 'No se proporcionaron datos'}), 400
        
        resultado = {'success': True, 'mensajes': []}
        
        # Buscar paciente
        nombre = (datos.get('nombre_completo') or '').upper().strip()
        expediente = (datos.get('expediente') or '').strip().upper()
        patient_id = None
        
        if expediente:
            p = get_patient_by_expediente(expediente)
            if p:
                patient_id = p['id']
                resultado['mensajes'].append('Paciente encontrado por expediente')
        
        if not patient_id and nombre:
            pacientes = get_all_patients(status='ingreso')
            for p in pacientes:
                pname = (p.get('nombre_completo') or '').upper()
                if nombre in pname or pname in nombre:
                    patient_id = p['id']
                    resultado['mensajes'].append('Paciente encontrado por nombre')
                    break
        
        # Crear paciente nuevo si es historia_clinica
        if not patient_id and tipo == 'historia_clinica' and nombre:
            patient_data = {
                'nombre_completo': nombre,
                'expediente': expediente,
                'edad': datos.get('edad'),
                'sexo': datos.get('sexo'),
                'diagnostico_ingreso': datos.get('diagnostico') or 'Por definir',
                'fecha_ingreso': datos.get('fecha') or date.today().isoformat(),
                'estado': 'ingreso'
            }
            # Campos numéricos - convertir a int/float
            int_campos = ['fc', 'fr', 'tas', 'tad', 'spo2', 'fio2', 'glasgow', 'edad']
            float_campos = ['temperatura', 'peso_estimado', 'talla', 'sao2', 'glasgow']
            
            for campo in int_campos:
                val = datos.get(campo)
                if val is not None and val != '':
                    try:
                        patient_data[campo] = int(float(val))
                    except (ValueError, TypeError):
                        pass
            
            for campo in float_campos:
                val = datos.get(campo)
                if val is not None and val != '':
                    try:
                        patient_data[campo] = float(val)
                    except (ValueError, TypeError):
                        pass
            
            patient_data = {k:v for k,v in patient_data.items() if v is not None and v != ''}
            patient_id = insert_patient(patient_data)
            
            if patient_id:
                resultado['paciente'] = {'id': patient_id, 'nombre_completo': nombre}
                resultado['mensajes'].append(f'Nuevo paciente creado: {nombre}')
            else:
                return jsonify({'success': False, 'error': 'Error al crear paciente'}), 500
        
        # Si es nota_evolucion y no hay paciente → error
        if not patient_id and tipo == 'nota_evolucion':
            return jsonify({
                'success': False,
                'error': 'Paciente no encontrado. Especifique expediente o nombre válido, o cree el paciente primero.'
            }), 400
        
        # Crear evolución
        if patient_id:
            evo = {
                'fecha': datos.get('fecha') or date.today().isoformat(),
                'hora': datos.get('hora') or datetime.now().strftime('%H:%M'),
                # Signos vitales
                'fc': datos.get('fc'), 'fr': datos.get('fr'),
                'tas': datos.get('tas'), 'tad': datos.get('tad'),
                'temperatura': datos.get('temperatura'),
                'spo2': datos.get('spo2'), 'fio2': datos.get('fio2'),
                'glasgow': datos.get('glasgow'),
                # Balance de liquidos
                'ingresos': datos.get('ingresos'),
                'egresos': datos.get('egresos'),
                'diuresis': datos.get('diuresis'),
                'drenajes': datos.get('drenajes'),
                'balance': datos.get('balance'),
                # Laboratorios - Quimica sanguinea
                'sodio': datos.get('sodio'),
                'potasio': datos.get('potasio'),
                'cloro': datos.get('cloro'),
                'calcio': datos.get('calcio'),
                'magnesio': datos.get('magnesio'),
                'fosforo': datos.get('fosforo'),
                'creatinina': datos.get('creatinina'),
                'glucosa': datos.get('glucosa'),
                'urea': datos.get('urea'),
                # Hematologia
                'hemoglobina': datos.get('hemoglobina'),
                'hematocrito': datos.get('hematocrito'),
                'leucocitos': datos.get('leucocitos'),
                'neutrofilos': datos.get('neutrofilos'),
                'plaquetas': datos.get('plaquetas'),
                # Gasometria
                'ph': datos.get('ph'),
                'lactato': datos.get('lactato'),
                # Inflamacion
                'pcr': datos.get('pcr'),
                # Notas
                'subjetivo': datos.get('subjetivo'),
                'objetivo': datos.get('objetivo'),
                'analisis': datos.get('analisis'),
                'plan': datos.get('plan') or 'Continuar manejo actual',
                'tipo': 'evolucion'
            }
            
            # Convertir tipos numéricos para evolución
            int_campos_evo = ['fc', 'fr', 'tas', 'tad', 'spo2', 'fio2', 'glasgow', 'ingresos', 'egresos', 'diuresis']
            float_campos_evo = ['temperatura', 'sodio', 'potasio', 'cloro', 'calcio', 'magnesio', 'fosforo', 
                                'creatinina', 'glucosa', 'urea', 'hemoglobina', 'hematocrito', 'leucocitos',
                                'neutrofilos', 'plaquetas', 'ph', 'lactato', 'pcr']
            
            for campo in int_campos_evo:
                if evo[campo] is not None and evo[campo] != '':
                    try:
                        evo[campo] = int(float(evo[campo]))
                    except (ValueError, TypeError):
                        evo[campo] = None
            
            for campo in float_campos_evo:
                if evo[campo] is not None and evo[campo] != '':
                    try:
                        evo[campo] = float(evo[campo])
                    except (ValueError, TypeError):
                        evo[campo] = None
            
            evo = {k:v for k,v in evo.items() if v is not None and v != ''}
            
            evo_id = create_evolution(patient_id, evo)
            if evo_id:
                resultado['evolucion'] = {
                    'id': evo_id,
                    'fecha': evo['fecha'],
                    'hora': evo['hora']
                }
                resultado['mensajes'].append(f'Evolución guardada: {evo["fecha"]} {evo["hora"]}')
            
            resultado['redirect_url'] = url_for('view_patient', id=patient_id)
        
        return jsonify(resultado)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR en api_import_execute: {error_msg}")
        print(error_trace[:500])
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': error_trace
        }), 500


def extraer_datos_clinicos(texto, tipo):
    """Extrae datos estructurados de texto clínico libre."""
    datos = {}
    
    # Nombre - limitar a solo palabras, no capturar líneas siguientes
    nombre_match = re.search(
        r'(?:paciente|nombre|patient|name)[\s:]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,5})(?:\s|$|\n)',
        texto, re.IGNORECASE
    )
    if nombre_match:
        datos['nombre_completo'] = nombre_match.group(1).strip().upper()
    
    # Edad
    edad_match = re.search(r'(\d+)\s*años?', texto, re.IGNORECASE)
    if edad_match:
        datos['edad'] = int(edad_match.group(1))
    
    # Sexo
    if re.search(r'\bfemenino\b|\bmujer\b', texto, re.IGNORECASE):
        datos['sexo'] = 'F'
    elif re.search(r'\bmasculino\b|\bhombre\b', texto, re.IGNORECASE):
        datos['sexo'] = 'M'
    
    # Expediente
    exp_match = re.search(
        r'(?:expediente|exp|folio|record)[\s:#]+([A-Z0-9\-]+)',
        texto, re.IGNORECASE
    )
    if exp_match:
        datos['expediente'] = exp_match.group(1).strip().upper()
    
    # Fecha
    fecha_match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', texto)
    if fecha_match:
        d1, d2, d3 = fecha_match.groups()
        if len(d3) == 2:
            d3 = '20' + d3
        datos['fecha'] = f"{d3}-{d2.zfill(2)}-{d1.zfill(2)}"
    
    # Hora
    hora_match = re.search(r'(\d{1,2}):(\d{2})', texto)
    if hora_match:
        datos['hora'] = f"{hora_match.group(1).zfill(2)}:{hora_match.group(2)}"
    
    # Signos vitales - TA soporta TAS/TAD o TA genérico
    fc_match = re.search(r'(?:FC|HR)[\s:]+(\d+)', texto, re.IGNORECASE)
    if fc_match:
        datos['fc'] = int(fc_match.group(1))
    
    fr_match = re.search(r'(?:FR|RR)[\s:]+(\d+)', texto, re.IGNORECASE)
    if fr_match:
        datos['fr'] = int(fr_match.group(1))
    
    ta_match = re.search(r'(?:TA|SBP|TAS)[\s:]+(\d+)[/\s]+(\d+)', texto, re.IGNORECASE)
    if ta_match:
        datos['tas'] = int(ta_match.group(1))
        datos['tad'] = int(ta_match.group(2))
    
    temp_match = re.search(r'(?:temp|temperatura)[\s:]+(\d+\.?\d*)', texto, re.IGNORECASE)
    if temp_match:
        datos['temperatura'] = float(temp_match.group(1))
    
    spo2_match = re.search(r'(?:SpO2|sat)[\s:]+(\d+)', texto, re.IGNORECASE)
    if spo2_match:
        datos['spo2'] = int(spo2_match.group(1))
    
    fio2_match = re.search(r'(?:FiO2)[\s:]+(\d+)', texto, re.IGNORECASE)
    if fio2_match:
        datos['fio2'] = int(fio2_match.group(1))
    
    glasgow_match = re.search(r'(?:GCS|glasgow)[\s:]+(\d+)', texto, re.IGNORECASE)
    if glasgow_match:
        datos['glasgow'] = int(glasgow_match.group(1))
    
    # Labs básicos
    labs = {
        'glucosa': r'gluc(?:osa)?[\s:]+(\d+\.?\d*)',
        'creatinina': r'creat(?:inina)?[\s:]+(\d+\.?\d*)',
        'hemoglobina': r'(?:Hb|hemoglobina)[\s:]+(\d+\.?\d*)',
        'leucocitos': r'(?:leucocitos|WBC|LEU)[\s:]+(\d+\.?\d*)',
        'plaquetas': r'(?:plaquetas|PLT)[\s:]+(\d+\.?\d*)',
        'lactato': r'(?:lactato|LCT)[\s:]+(\d+\.?\d*)',
        'hematocrito': r'(?:HTC|HCT|hematocrito)[\s:]+(\d+\.?\d*)',
        'neutrofilos': r'NEU[\s:]+(\d+\.?\d*)',
        'pcr': r'PCR[\s:]+(\d+\.?\d*)',
    }
    for campo, pattern in labs.items():
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            try:
                datos[campo] = float(match.group(1))
            except:
                pass
    
    # Electrolitos - patrones específicos con word boundaries
    # Sodio: NA como palabra completa
    sodio_match = re.search(r'(?:^|\s||,)\s*NA\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE)
    if sodio_match:
        datos['sodio'] = float(sodio_match.group(1))
    else:
        sodio_match = re.search(r'(?:^|\s|)sodio[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
        if sodio_match:
            datos['sodio'] = float(sodio_match.group(1))
    
    # Potasio: K como palabra completa
    potasio_match = re.search(r'(?:^|\s||,)\s*K\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE)
    if potasio_match:
        datos['potasio'] = float(potasio_match.group(1))
    else:
        potasio_match = re.search(r'(?:^|\s|)potasio[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
        if potasio_match:
            datos['potasio'] = float(potasio_match.group(1))
    
    # Cloro: CL como palabra completa
    cloro_match = re.search(r'(?:^|\s||,)\s*CL\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE)
    if cloro_match:
        datos['cloro'] = float(cloro_match.group(1))
    else:
        cloro_match = re.search(r'(?:^|\s|)cloro[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
        if cloro_match:
            datos['cloro'] = float(cloro_match.group(1))
    
    # Fósforo: buscar "FOSFORO" primero, luego "P" con validación de rango
    fosforo_match = re.search(r'(?:^|\s|)f[oó]sforo[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
    if fosforo_match:
        val = float(fosforo_match.group(1))
        if val <= 20:  # Valor razonable para fósforo
            datos['fosforo'] = val
    else:
        # Buscar "P" como palabra completa
        fosforo_matches = list(re.finditer(r'(?:^|\s||,)\s*P\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE))
        for m in fosforo_matches:
            val = float(m.group(1))
            if val <= 20:  # Fósforo normalmente entre 1-10
                datos['fosforo'] = val
                break
    
    # Magnesio: MG como palabra completa (no confundir con mg/dL)
    magnesio_match = re.search(r'(?:^|\s||,)\s*MG\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE)
    if magnesio_match:
        val = float(magnesio_match.group(1))
        if val <= 10:  # Magnesio normalmente 1-5
            datos['magnesio'] = val
    else:
        magnesio_match = re.search(r'(?:^|\s|)magnesio[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
        if magnesio_match:
            val = float(magnesio_match.group(1))
            if val <= 10:
                datos['magnesio'] = val
    
    # Calcio: CA como palabra completa
    calcio_match = re.search(r'(?:^|\s||,)\s*CA\s+(\d+\.?\d*)(?:\s|$||,)', texto, re.IGNORECASE | re.MULTILINE)
    if calcio_match:
        datos['calcio'] = float(calcio_match.group(1))
    else:
        calcio_match = re.search(r'(?:^|\s|)calcio[\s:]+(\d+\.?\d*)(?:\s|$|)', texto, re.IGNORECASE | re.MULTILINE)
        if calcio_match:
            datos['calcio'] = float(calcio_match.group(1))
    
    # BUN
    bun_match = re.search(r'(?:BUN|bun)[\s:]+(\d+\.?\d*)', texto, re.IGNORECASE)
    if bun_match:
        datos['bun'] = float(bun_match.group(1))
    
    # Secciones de nota
    subj_match = re.search(
        r'(?:MOTIVO|MOTIVO\s+DE\s+INGRESO|SUBJETIVO)[\s:]*(.+?)(?=OBJETIVO|EXAMEN|EXPLORACI[oó]N|SIGNOS|PLAN|\Z)',
        texto, re.IGNORECASE | re.DOTALL
    )
    if subj_match:
        datos['subjetivo'] = subj_match.group(1).strip()[:500]
    
    obj_match = re.search(
        r'(?:OBJETIVO|EXAMEN|EXPLORACI[oó]N)[\s:]*(.+?)(?=AN[aá]LISIS|DIAGN[oó]STICO|PLAN|\Z)',
        texto, re.IGNORECASE | re.DOTALL
    )
    if obj_match:
        datos['objetivo'] = obj_match.group(1).strip()[:1000]
    
    analisis_match = re.search(
        r'(?:AN[aá]LISIS|DIAGN[oó]STICO)[\s:]*(.+?)(?=PLAN|\Z)',
        texto, re.IGNORECASE | re.DOTALL
    )
    if analisis_match:
        datos['analisis'] = analisis_match.group(1).strip()[:500]
    
    plan_match = re.search(r'(?:PLAN|TRATAMIENTO)[\s:]*(.+?)(?=\Z)', texto, re.IGNORECASE | re.DOTALL)
    if plan_match:
        datos['plan'] = plan_match.group(1).strip()[:1000]
    
    # Diagnóstico
    diag_match = re.search(
        r'(?:DIAGN[oó]STICO\s+DE\s+INGRESO|DIAGN[oó]STICO\s+PRINCIPAL)[\s:]*(.+?)(?=\n|\Z)',
        texto, re.IGNORECASE
    )
    if diag_match:
        datos['diagnostico'] = diag_match.group(1).strip()[:200]
    
    return datos


# ============================================================================
# MAIN
# ============================================================================



# ============================================================
# VISTA AX - ANÁLISIS DE TENDENCIAS
# ============================================================

@app.route('/analysis')
@login_required
def analysis_page():
    """Vista de análisis de tendencias clínicas (AX) - Vista moderna."""
    patients = get_all_patients()
    logger.info(f"Rendering ax_dashboard.html for /analysis with {len(patients)} patients")
    response = make_response(render_template('ax_dashboard.html', patients=patients))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['CDN-Cache-Control'] = 'no-cache'  # Cloudflare
    response.headers['Cloudflare-CDN-Cache-Control'] = 'no-cache'  # Cloudflare
    return response


@app.route('/api/patient/<int:patient_id>/trends', methods=['GET'])
@login_required
def api_patient_trends(patient_id):
    """Retorna datos de evolución para tendencias."""
    
    # Debug: log cookies recibidas
    logger.info(f"API trends cookies: session_token={session.get('session_token')}, cookies={list(request.cookies.keys())}")
    
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    limit = request.args.get('limit', type=int)
    # Si no se especifica límite, traer todas las evoluciones
    if limit:
        evolutions = get_evolutions(patient_id, limit=limit)
    else:
        evolutions = get_evolutions(patient_id, limit=10000)  # Prácticamente todas
    
    logger.info(f"API trends: patient_id={patient_id}, evolutions={len(evolutions)}")
    
    # Serializar evoluciones (convertir time/date a strings)
    serializable_evolutions = []
    for evo in evolutions:
        serializable = {}
        for key, value in evo.items():
            if hasattr(value, 'isoformat'):
                serializable[key] = value.isoformat()
            elif value is None:
                serializable[key] = None
            else:
                serializable[key] = value
        serializable_evolutions.append(serializable)
    
    return jsonify({
        'patient_id': patient_id,
        'nombre_completo': patient.get('nombre_completo'),
        'evoluciones': serializable_evolutions,
        'count': len(serializable_evolutions)
    })


@app.route('/api/patient/<int:patient_id>/trends/chart', methods=['GET'])
@login_required
def api_patient_trends_chart(patient_id):
    """Genera gráfica PNG base64 de tendencias."""
    from flask import request
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    chart_type = request.args.get('type', 'vitals')
    theme = request.args.get('theme', 'dark')
    limit = request.args.get('limit', type=int)
    
    # Si no se especifica límite, traer todas las evoluciones
    if limit:
        evolutions = get_evolutions(patient_id, limit=limit)
    else:
        evolutions = get_evolutions(patient_id, limit=10000)  # Prácticamente todas
    if not evolutions:
        return jsonify({'error': 'Sin evoluciones'}), 404
    
    # Mapear tipos del frontend a tipos del backend
    chart_type_map = {
        'main': 'vitals',
        'vitals': 'vitals',
        'liquids': 'liquids',
        'renal': 'labs',
        'ventilatory': 'vitals',
        'metabolic': 'labs',
        'hematologic': 'labs',
        'labs': 'labs'
    }
    backend_type = chart_type_map.get(chart_type, chart_type)
    
    # Generar gráfica según tipo
    if backend_type == 'vitals':
        image_b64 = generate_vitals_chart(evolutions)
        title = 'Signos Vitales'
    elif backend_type == 'liquids':
        image_b64 = generate_liquids_chart(evolutions)
        title = 'Balance Hídrico'
    elif backend_type == 'labs':
        image_b64 = generate_labs_chart(evolutions)
        title = 'Laboratorios'
    else:
        # Personalizado: parsear parámetros de query string
        params = []
        for key in request.args:
            if key.startswith('param_'):
                param_name = key.replace('param_', '')
                label = request.args.get(f'label_{param_name}', param_name)
                color = request.args.get(f'color_{param_name}', '#4ade80')
                params.append({'campo': param_name, 'label': label, 'color': color})
        
        if not params:
            params = [
                {'campo': 'fc', 'label': 'FC', 'color': '#ef4444'},
                {'campo': 'fr', 'label': 'FR', 'color': '#f97316'}
            ]
        image_b64 = generate_trend_chart(evolutions, params, "Tendencias Personalizadas", theme)
        title = 'Personalizado'
    
    if not image_b64:
        return jsonify({'error': 'No se pudo generar gráfica'}), 500
    
    return jsonify({
        'patient_id': patient_id,
        'chart_type': chart_type,
        'title': title,
        'image': f'data:image/png;base64,{image_b64}',
        'count': len(evolutions)
    })

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/debug-template')
@login_required
def debug_template():
    """Debug: muestra qué template se está renderizando."""
    patients = get_all_patients()
    return f"Template: ax_dashboard.html<br>Patients count: {len(patients)}<br>Template exists: True"

@app.route('/test-analysis')
def test_analysis():
    """Endpoint de prueba sin autenticación para verificar template."""
    patients = get_all_patients()
    response = make_response(render_template('ax_dashboard.html', patients=patients))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    return response


# ============================================================================
# AUTO-RECALCULO DE ANALYTICS
# ============================================================================

def auto_recalculate_analytics(patient_id):
    """Recalcula automáticamente métricas analytics después de cambios."""
    try:
        from modules.clinical_analytics import calculate_advanced_metrics, save_analytics
        patient = get_patient(patient_id)
        if patient:
            evolutions = get_evolutions(patient_id)
            metrics = calculate_advanced_metrics(patient, evolutions)
            compliance = calculate_patient_compliance(patient_id)
            save_analytics(patient_id, metrics, compliance)
            app.logger.info(f"Analytics recalculados para paciente {patient_id}")
    except Exception as e:
        app.logger.error(f"Error auto-recalculando analytics: {e}")

# ============================================================================
# INDICADORES DE CUMPLIMIENTO (COMPLIANCE SCORING)
# ============================================================================

# Campos críticos para evaluar completitud
def get_critical_ingreso_fields():
    """Retorna campos críticos del formulario de ingreso."""
    return {
        # Demográficos (4)
        'nombre_completo', 'edad', 'sexo', 'fecha_ingreso',
        # Signos vitales (7)
        'fc', 'fr', 'tas', 'tad', 'tam', 'temperatura', 'spo2',
        # Ventilatorio (3)
        'modo_ventilatorio', 'fio2', 'peep',
        # Labs críticos (5)
        'creatinina', 'leucocitos', 'plaquetas', 'hemoglobina', 'glucosa',
        # Diagnóstico y scores (4)
        'diagnostico_ingreso', 'sofa_ingreso', 'apache2_ingreso', 'news2_ingreso',
        # Hemodinámica (3)
        'glasgow', 'rass', 'talla',
    }

def get_critical_evolution_fields():
    """Retorna campos críticos de cada evolución."""
    return {
        # Signos vitales (7)
        'fc', 'tas', 'tad', 'tam', 'temperatura', 'spo2', 'fio2',
        # Labs básicos (4)
        'creatinina', 'glucosa', 'leucocitos', 'plaquetas',
        # Ventilatorio (3)
        'modo_ventilatorio', 'peep', 'ppico',
        # Nota clínica (4)
        'subjetivo', 'objetivo', 'analisis', 'plan',
        # Balance (2)
        'ingresos', 'egresos',
    }

def calculate_patient_compliance(patient_id):
    """
    Calcula indicadores de cumplimiento para un paciente.
    
    Retorna dict con:
    - ingreso_compliance: % de campos críticos de ingreso completos
    - evolution_coverage: ratio de evoluciones/días de estancia
    - evolution_compliance: % promedio de campos críticos en evoluciones
    - overall_score: promedio ponderado de los 3 indicadores
    - color: 'green' | 'yellow' | 'red' según overall_score
    - details: dict con conteos detallados
    """
    from datetime import datetime, date
    
    patient = get_patient(patient_id)
    if not patient:
        return None
    
    # ============ 1. CUMPLIMIENTO DE INGRESO ============
    ingreso_critical = get_critical_ingreso_fields()
    ingreso_total = len(ingreso_critical)
    ingreso_filled = sum(1 for f in ingreso_critical if patient.get(f) not in (None, '', [], {}, 0))
    # Nota: 0 puede ser válido para algunos campos, pero para scoring simple lo contamos como vacío
    # Re-evaluar campos numéricos
    numeric_fields = {'edad', 'fc', 'fr', 'tas', 'tad', 'tam', 'temperatura', 'spo2', 'fio2', 'peep',
                      'creatinina', 'leucocitos', 'plaquetas', 'hemoglobina', 'glucosa',
                      'sofa_ingreso', 'apache2_ingreso', 'news2_ingreso', 'talla'}
    ingreso_filled = 0
    for f in ingreso_critical:
        val = patient.get(f)
        if val is None:
            continue
        if isinstance(val, str) and val.strip() == '':
            continue
        if f in numeric_fields and val in (0, 0.0, '0', '0.0'):
            # 0 puede ser válido pero para scoring lo consideramos incompleto
            # excepto si es explícitamente reportado (verificamos si hay otros campos llenos)
            continue
        ingreso_filled += 1
    
    ingreso_score = round((ingreso_filled / ingreso_total) * 100, 1) if ingreso_total > 0 else 0
    
    # ============ 2. COBERTURA DE EVOLUCIONES ============
    evolutions = get_evolutions(patient_id)
    
    # Calcular días de estancia
    fecha_ingreso = patient.get('fecha_ingreso_uci') or patient.get('fecha_ingreso')
    if fecha_ingreso:
        try:
            if hasattr(fecha_ingreso, 'isoformat'):
                fecha_ingreso = fecha_ingreso.isoformat()
            ingreso_dt = datetime.strptime(str(fecha_ingreso)[:10], '%Y-%m-%d').date()
            # Si tiene fecha de egreso, usar esa; si no, hoy
            fecha_egreso = patient.get('fecha_egreso_uci') or patient.get('fecha_egreso_hospital')
            if fecha_egreso:
                if hasattr(fecha_egreso, 'isoformat'):
                    fecha_egreso = fecha_egreso.isoformat()
                egreso_dt = datetime.strptime(str(fecha_egreso)[:10], '%Y-%m-%d').date()
            else:
                egreso_dt = date.today()
            dias_estancia = max(1, (egreso_dt - ingreso_dt).days)
        except:
            dias_estancia = 1
    else:
        dias_estancia = 1
    
    # Contar evoluciones únicas por día
    evo_dates = set()
    for evo in evolutions:
        fecha = evo.get('fecha')
        if fecha:
            if hasattr(fecha, 'isoformat'):
                fecha = fecha.isoformat()
            evo_dates.add(str(fecha)[:10])
    
    dias_con_evolucion = len(evo_dates)
    coverage_score = round((dias_con_evolucion / dias_estancia) * 100, 1) if dias_estancia > 0 else 0
    # Cap at 100%
    coverage_score = min(100, coverage_score)
    
    # ============ 3. CUMPLIMIENTO DE CAMPOS EN EVOLUCIONES ============
    evo_critical = get_critical_evolution_fields()
    evo_total = len(evo_critical)
    
    if evolutions:
        evo_scores = []
        for evo in evolutions:
            filled = 0
            for f in evo_critical:
                val = evo.get(f)
                if val is None:
                    continue
                if isinstance(val, str) and val.strip() == '':
                    continue
                filled += 1
            evo_scores.append(filled)
        avg_evo_filled = sum(evo_scores) / len(evo_scores)
        evolution_score = round((avg_evo_filled / evo_total) * 100, 1) if evo_total > 0 else 0
    else:
        evolution_score = 0
    
    # ============ 4. OVERALL SCORE ============
    # Fórmula: promedio simple de los 3
    overall = round((ingreso_score + coverage_score + evolution_score) / 3, 1)
    
    # Color según score
    if overall >= 80:
        color = 'green'
        color_hex = '#4ADE80'
        label = 'Bueno'
    elif overall >= 50:
        color = 'yellow'
        color_hex = '#FACC15'
        label = 'Regular'
    else:
        color = 'red'
        color_hex = '#F87171'
        label = 'Deficiente'
    
    return {
        'ingreso_compliance': ingreso_score,
        'evolution_coverage': coverage_score,
        'evolution_compliance': evolution_score,
        'overall_score': overall,
        'color': color,
        'color_hex': color_hex,
        'label': label,
        'details': {
            'ingreso_filled': ingreso_filled,
            'ingreso_total': ingreso_total,
            'dias_estancia': dias_estancia,
            'dias_con_evolucion': dias_con_evolucion,
            'total_evoluciones': len(evolutions),
            'avg_evo_filled': round(avg_evo_filled, 1) if evolutions else 0,
            'evo_total_fields': evo_total,
            'evoluciones_por_dia': round(len(evolutions) / dias_estancia, 2) if dias_estancia > 0 and evolutions else 0,
        }
    }


@app.route('/api/patient/<int:patient_id>/compliance', methods=['GET'])
@login_required
def api_patient_compliance(patient_id):
    """Retorna indicadores de cumplimiento del expediente."""
    result = calculate_patient_compliance(patient_id)
    if result is None:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    return jsonify(result)



# ============================================================================
# ENDPOINT DE ANÁLISIS CLÍNICO AVANZADO (ANALYTICS)
# ============================================================================

@app.route('/api/patient/<int:patient_id>/analytics', methods=['GET'])
@login_required
def api_patient_analytics(patient_id):
    """Retorna métricas analíticas calculadas del paciente."""
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    # Intentar obtener métricas guardadas
    analytics = get_analytics(patient_id)
    
    if analytics:
        # Convertir valores serializables
        serializable = {}
        for key, value in analytics.items():
            if hasattr(value, 'isoformat'):
                serializable[key] = value.isoformat()
            elif value is None:
                serializable[key] = None
            else:
                serializable[key] = value
        return jsonify({
            'patient_id': patient_id,
            'calculated': True,
            'cached': True,
            'metrics': serializable
        })
    else:
        # Calcular al vuelo
        try:
            evolutions = get_evolutions(patient_id)
            metrics = calculate_advanced_metrics(patient, evolutions)
            
            # Calcular compliance
            compliance = calculate_patient_compliance(patient_id)
            
            # Guardar para futuras consultas
            save_analytics(patient_id, metrics, compliance)
            
            return jsonify({
                'patient_id': patient_id,
                'calculated': True,
                'cached': False,
                'metrics': metrics,
                'compliance': compliance
            })
        except Exception as e:
            logger.error(f"Error calculando analytics: {e}")
            return jsonify({'error': f'Error en cálculo: {str(e)}'}), 500


@app.route('/api/patient/<int:patient_id>/analytics/recalculate', methods=['POST'])
@login_required
def api_patient_analytics_recalculate(patient_id):
    """Fuerza el recálculo de métricas analíticas."""
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    try:
        evolutions = get_evolutions(patient_id)
        metrics = calculate_advanced_metrics(patient, evolutions)
        compliance = calculate_patient_compliance(patient_id)
        
        save_analytics(patient_id, metrics, compliance)
        
        return jsonify({
            'patient_id': patient_id,
            'recalculated': True,
            'metrics': metrics,
            'compliance': compliance
        })
    except Exception as e:
        logger.error(f"Error recalculando analytics: {e}")
        return jsonify({'error': f'Error en recálculo: {str(e)}'}), 500


@app.route('/api/admin/analytics/recalculate-all', methods=['POST'])
@login_required
def api_admin_recalculate_all():
    """Recalcula métricas para TODOS los pacientes. Solo admin."""
    # Verificar que es admin (implementar según tu lógica de roles)
    # Por ahora, permitir a cualquier usuario autenticado
    try:
        from modules.clinical_analytics import recalculate_all_analytics
        count = recalculate_all_analytics()
        return jsonify({'recalculated': count, 'status': 'success'})
    except Exception as e:
        logger.error(f"Error recalculando todos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/public-test/<int:patient_id>/trends')
def public_test_trends(patient_id):
    """Endpoint público de prueba para verificar datos sin autenticación."""
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    
    evolutions = get_evolutions(patient_id, limit=5)
    serializable_evolutions = []
    for evo in evolutions:
        serializable = {}
        for key, value in evo.items():
            if hasattr(value, 'isoformat'):
                serializable[key] = value.isoformat()
            elif value is None:
                serializable[key] = None
            else:
                serializable[key] = value
        serializable_evolutions.append(serializable)
    
    return jsonify({
        'patient_id': patient_id,
        'nombre_completo': patient.get('nombre_completo'),
        'evoluciones': serializable_evolutions,
        'count': len(serializable_evolutions)
    })
# API endpoints para tablas dinámicas (PUT y DELETE)

@app.route('/api/dynamic/<string:table_name>/<int:item_id>', methods=['PUT', 'DELETE'])
@login_required
def api_dynamic_item(table_name, item_id):
    """API para actualizar o eliminar items de tablas dinámicas."""
    from modules.database import update_dynamic_item, delete_dynamic_item
    
    if request.method == 'PUT':
        data = request.get_json() or {}
        success = update_dynamic_item(table_name, item_id, data)
        if success:
            return jsonify({'success': True, 'message': 'Item actualizado correctamente'})
        return jsonify({'success': False, 'error': 'Error al actualizar item'}), 400
    
    elif request.method == 'DELETE':
        success = delete_dynamic_item(table_name, item_id)
        if success:
            return jsonify({'success': True, 'message': 'Item eliminado correctamente'})
        return jsonify({'success': False, 'error': 'Error al eliminar item'}), 400


if __name__ == '__main__':
    print("="*60)
    print("SINAPSID DMA - Iniciando servidor...")
    print("URL: http://localhost:5001")
    print("Health: http://localhost:5001/health")
    print("="*60)
    # PRODUCCION: debug=False para seguridad
    app.run(debug=False, host='0.0.0.0', port=5001)



