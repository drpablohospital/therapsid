"""
SINAPSID DMA - Módulo de Base de Datos
======================================
Operaciones PostgreSQL para el sistema clínico SINAPSID-DMA.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE_URL


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager para conexiones a PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor(cursor_factory=None):
    """Context manager para cursores de PostgreSQL."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor, conn
        finally:
            cursor.close()


def dict_from_row(row):
    """Convierte una fila de RealDictRow a diccionario Python."""
    if row is None:
        return None
    return dict(row)


# ============================================================================
# PATIENT OPERATIONS
# ============================================================================

def get_patient_fields():
    """Retorna la lista de campos de la tabla patients."""
    return [
        'id', 'created_at', 'updated_at', 'nombre_completo', 'fecha_nacimiento',
        'edad', 'sexo', 'procedencia', 'servicio_tratante', 'fecha_ingreso_hosp',
        'fecha_ingreso', 'dias_estancia', 'cama', 'expediente', 'curp', 'episodio',
        'cpot', 'rass', 'glasgow', 'reflejo_pupilar', 'reflejo_corneal',
        'reflejo_tusigeno', 'rots', 'pupilas_mm', 'exploracion_neurologica',
        'imagen_neurologica', 'mottling', 'llenado_capilar', 'tas', 'tad', 'tam',
        'fc', 'ekg', 'exploracion_hemodinamica', 'talla', 'peso_ideal', 'fr',
        'sao2', 'disnea', 'o2_suplementario', 'fio2', 'modo_ventilatorio',
        'inicio_ventilador', 'traqueostomia_ingreso', 'numero_tubo', 'arcada',
        'vt_psinp', 'vt_peso', 'peep', 'relacion_ie', 'ppico', 'pplat',
        'vol_min', 'driving_pressure', 'p0_1', 'nif', 'tos', 'exploracion_ventilatoria',
        'imagen_ventilatoria', 'blue', 'gasometria_fecha', 'gasometria_ph',
        'gasometria_hco3', 'gasometria_pco2', 'gasometria_po2', 'gasometria_lactato',
        'tobin', 'pafi', 'vent_otros', 'sonda_vesical', 'peso_estimado',
        'periodo_horas', 'diuresis_total', 'indice_urinario', 'ingresos', 'egresos',
        'balance', 'balance_global', 'bun', 'urea', 'creatinina', 'sodio', 'potasio',
        'cloro', 'fosforo', 'magnesio', 'calcio', 'ego', 'tfg', 'fena', 'febun',
        'osmolaridad', 'imc', 'peso_ajustado', 'ayuno', 'gastrostomia_ingreso',
        'sonda_levin', 'proteinas_slider', 'proteinas_requeridas', 'kcal_100ml', 'prot_100ml',
        'tipo_nutricion', 'producto_nutricion', 'volumen_aporte', 'kcal_aporte', 'proteinas_aporte',
        'ml_24h_calc', 'ml_h_calc', 'kcal_totales_calc', 'kcal_kg_calc',
        'pct_kcal_calc', 'glucemia_capilar', 'insulina_glargina', 'insulina_rapida',
        'evacuaciones', 'bristol', 'glucosa_central', 'bilirrubina_total',
        'bilirrubina_directa', 'bilirrubina_indirecta', 'albumina', 'proteinas_totales',
        'alt', 'ast', 'dhl', 'fosfatasa_alcalina', 'amilasa', 'lipasa',
        'exploracion_gastro', 'drenajes', 'temperatura', 'petequias', 'sangrado',
        'trombosis', 'leucocitos', 'neutrofilos', 'linfocitos', 'hemoglobina',
        'hematocrito', 'plaquetas', 'pcr', 'pct', 'vsg', 'troponina', 'bnp',
        'dimero_d', 'tp', 'ttp', 'inr', 'fibrinogeno', 'exploracion_hema',
        'padecimiento_actual', 'evolucion_previa',
        'charlson_edad', 'charlson_im', 'charlson_evc', 'charlson_ep',
        'charlson_demencia', 'charlson_epoc', 'charlson_tejido_conectivo',
        'charlson_ulcera_peptica', 'charlson_enfermedad_hepatica_leve',
        'charlson_enfermedad_hepatica_moderada', 'charlson_insuficiencia_renal',
        'charlson_dmi', 'charlson_dmii', 'charlson_hemiparesia',
        'charlson_leucemia', 'charlson_linfoma', 'charlson_tumor_solido',
        'charlson_tumor_metastasis', 'charlson_sida', 'charlson_total',
        'charlson_mortalidad',
        'diagnostico_ingreso', 'plan_ingreso', 'news2_ingreso', 'news2_interpretado',
        'sofa_ingreso', 'sofa_mortalidad', 'sofa2_ingreso', 'apache2_ingreso',
        'apache2_mortalidad', 'saps3_ingreso', 'saps3_mortalidad', 'swift_score',
        'fc_egreso', 'fr_egreso', 'tas_egreso', 'tad_egreso', 'tam_egreso',
        'sao2_egreso', 'fio2_egreso', 'pafi_egreso', 'temperatura_egreso',
        'hemoglobina_egreso', 'hematocrito_egreso', 'leucocitos_egreso',
        'plaquetas_egreso', 'neutrofilos_egreso', 'linfocitos_egreso', 'pcr_egreso',
        'pct_egreso', 'sodio_egreso', 'potasio_egreso', 'cloro_egreso',
        'creatinina_egreso', 'bun_egreso', 'urea_egreso', 'glucosa_egreso',
        'bilirrubina_total_egreso', 'bilirrubina_directa_egreso', 'albumina_egreso',
        'gasometria_ph_egreso', 'gasometria_pco2_egreso', 'gasometria_po2_egreso',
        'gasometria_hco3_egreso', 'gasometria_lactato_egreso', 'fecha_egreso_uci',
        'fecha_egreso_hospital', 'tipo_egreso', 'servicio_egreso', 'fecha_defuncion',
        'fecha_retiro_cvc', 'fecha_retiro_sonda_urinaria', 'fecha_extubacion',
        'diagnostico_egreso', 'plan_egreso', 'news2_egreso', 'sofa_egreso',
        'sofa2_egreso', 'apache2_egreso', 'saps_egreso', 'condicion_egreso',
        'destino_egreso', 'estado',
        # Campos adicionales de egreso (v2)
        'dias_ventilacion_mecanica', 'dias_sonda_urinaria_egreso',
        'infeccion_hai', 'hai_tipo', 'lesion_renal_aguda',
        'evento_quirurgico_estancia', 'es_reingreso', 'muerte_encefalica',
        'diagnostico_codificado'
    ]


def insert_patient(patient_data):
    """
    Inserta un nuevo paciente en la base de datos.
    
    Args:
        patient_data: Diccionario con datos del paciente
    
    Returns:
        int: ID del paciente creado
    
    Raises:
        Exception: Si hay error en la inserción
    """
    valid_fields = get_patient_fields()
    
    # Filtrar solo campos válidos
    filtered_data = {k: v for k, v in patient_data.items() if k in valid_fields}
    
    if not filtered_data:
        raise ValueError("No hay campos válidos para insertar")
    
    columns = ', '.join(filtered_data.keys())
    placeholders = ', '.join(['%s' for _ in filtered_data])
    values = list(filtered_data.values())
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"INSERT INTO patients ({columns}) VALUES ({placeholders}) RETURNING id",
            values
        )
        patient_id = cursor.fetchone()[0]
        conn.commit()
        return patient_id


def update_patient(patient_id, patient_data):
    """
    Actualiza un paciente existente.
    
    Args:
        patient_id: ID del paciente
        patient_data: Diccionario con datos a actualizar
    
    Returns:
        bool: True si se actualizó correctamente
    
    Raises:
        Exception: Si hay error en la actualización
    """
    valid_fields = get_patient_fields()
    
    # Filtrar solo campos válidos y no nulos
    filtered_data = {k: v for k, v in patient_data.items() 
                     if k in valid_fields and v is not None and k != 'id'}
    
    if not filtered_data:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered_data.keys()])
    values = list(filtered_data.values()) + [patient_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"UPDATE patients SET {set_clause} WHERE id = %s",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def get_patient(patient_id):
    """
    Obtiene un paciente por ID.
    
    Args:
        patient_id: ID del paciente
    
    Returns:
        dict: Datos del paciente o None si no existe
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT * FROM patients WHERE id = %s",
            (patient_id,)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def get_patient_by_expediente(expediente):
    """
    Obtiene un paciente por número de expediente.
    
    Args:
        expediente: Número de expediente
    
    Returns:
        dict: Datos del paciente o None si no existe
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT * FROM patients WHERE expediente = %s",
            (expediente,)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def get_all_patients(status=None):
    """
    Obtiene todos los pacientes, opcionalmente filtrados por estado.
    
    Args:
        status: 'ingreso', 'egreso' o None para todos
    
    Returns:
        list: Lista de diccionarios con datos de pacientes
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        if status:
            cursor.execute(
                "SELECT * FROM patients WHERE estado = %s ORDER BY cama ASC NULLS LAST",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM patients ORDER BY cama ASC NULLS LAST")
        
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def check_expediente_exists(expediente, exclude_id=None):
    """
    Verifica si un expediente ya existe.
    
    Args:
        expediente: Número de expediente a verificar
        exclude_id: ID a excluir de la verificación (para actualizaciones)
    
    Returns:
        bool: True si el expediente existe
    """
    if not expediente:
        return False
    
    with get_db_cursor() as (cursor, conn):
        if exclude_id:
            cursor.execute(
                "SELECT id FROM patients WHERE expediente = %s AND id != %s",
                (expediente, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT id FROM patients WHERE expediente = %s",
                (expediente,)
            )
        return cursor.fetchone() is not None


def discharge_patient(patient_id, discharge_data):
    """
    Marca un paciente como egresado.
    
    Args:
        patient_id: ID del paciente
        discharge_data: Diccionario con datos de egreso
    
    Returns:
        bool: True si se actualizó correctamente
    """
    valid_fields = get_patient_fields()
    
    # Filtrar solo campos válidos de egreso
    filtered_data = {k: v for k, v in discharge_data.items() 
                     if k in valid_fields and v is not None}
    filtered_data['estado'] = 'egreso'
    
    if not filtered_data:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered_data.keys()])
    values = list(filtered_data.values()) + [patient_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"UPDATE patients SET {set_clause} WHERE id = %s",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_patient(patient_id):
    """
    Elimina un paciente y todos sus registros asociados (cascade).
    
    Args:
        patient_id: ID del paciente
    
    Returns:
        bool: True si se eliminó correctamente
    """
    with get_db_cursor() as (cursor, conn):
        cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# DYNAMIC TABLES OPERATIONS
# ============================================================================

DYNAMIC_TABLE_SCHEMAS = {
    'medicamentos_neurologicos': ['medicamento', 'via', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'medicamentos_hemodinamicos': ['medicamento', 'via', 'unidad', 'dosis_max', 'dosis_min', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'medicamentos_nefro': ['medicamento', 'via', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
    'medicamentos_gastro': ['medicamento', 'via', 'unidad', 'dosis', 'fecha_inicio', 'fecha_fin'],
    'medicacion_hematologica': ['medicamento', 'via', 'dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'antibioticos': ['antibiotico', 'via', 'dosis', 'unidad', 'fecha_inicio', 'fecha_fin', 'indicacion'],
    'cultivos': ['tipo', 'fecha', 'resultado', 'microorganismo', 'sensibilidad', 'resistencia'],
    'transfusiones': ['componente', 'dosis_unidades', 'dosis_ml', 'fecha_transfusion', 'reaccion_adversa']
}

DYNAMIC_TABLE_LABELS = {
    'medicamentos_neurologicos': '💊 MEDICAMENTOS NEUROLÓGICOS',
    'medicamentos_hemodinamicos': '❤️ MEDICAMENTOS HEMODINÁMICOS',
    'medicamentos_nefro': '💧 MEDICAMENTOS RENALES',
    'medicamentos_gastro': '🍽️ MEDICAMENTOS GASTROINTESTINALES',
    'medicacion_hematologica': '🩸 MEDICACIÓN HEMATOLÓGICA',
    'antibioticos': '💊 ANTIBIÓTICOS',
    'cultivos': '🧫 CULTIVOS',
    'transfusiones': '🩸 TRANSFUSIONES'
}


def get_all_dynamic_tables(patient_id):
    """Obtiene todas las tablas dinámicas de un paciente."""
    result = {}
    for table_name in DYNAMIC_TABLE_SCHEMAS:
        result[table_name] = get_dynamic_items(table_name, patient_id)
    return result


def get_dynamic_items(table_name, patient_id):
    """
    Obtiene todos los items de una tabla dinámica para un paciente.
    
    Args:
        table_name: Nombre de la tabla
        patient_id: ID del paciente
    
    Returns:
        list: Lista de diccionarios con los items
    """
    if table_name not in DYNAMIC_TABLE_SCHEMAS:
        return []
    
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            f"SELECT * FROM {table_name} WHERE patient_id = %s ORDER BY id",
            (patient_id,)
        )
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def create_dynamic_item(table_name, patient_id, item_data):
    """
    Crea un nuevo item en una tabla dinámica.
    
    Args:
        table_name: Nombre de la tabla
        patient_id: ID del paciente
        item_data: Diccionario con datos del item
    
    Returns:
        int: ID del item creado
    """
    if table_name not in DYNAMIC_TABLE_SCHEMAS:
        return None
    
    valid_columns = DYNAMIC_TABLE_SCHEMAS[table_name]
    filtered_data = {k: v for k, v in item_data.items() if k in valid_columns}
    
    if not filtered_data:
        return None
    
    columns = ['patient_id'] + list(filtered_data.keys())
    placeholders = ['%s' for _ in columns]
    values = [patient_id] + list(filtered_data.values())
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id",
            values
        )
        item_id = cursor.fetchone()[0]
        conn.commit()
        return item_id


def update_dynamic_item(table_name, item_id, item_data):
    """
    Actualiza un item en una tabla dinámica.
    
    Args:
        table_name: Nombre de la tabla
        item_id: ID del item
        item_data: Diccionario con datos a actualizar
    
    Returns:
        bool: True si se actualizó correctamente
    """
    if table_name not in DYNAMIC_TABLE_SCHEMAS:
        return False
    
    valid_columns = DYNAMIC_TABLE_SCHEMAS[table_name]
    filtered_data = {k: v for k, v in item_data.items() 
                     if k in valid_columns and v is not None}
    
    if not filtered_data:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered_data.keys()])
    values = list(filtered_data.values()) + [item_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"UPDATE {table_name} SET {set_clause} WHERE id = %s",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_dynamic_item(table_name, item_id):
    """
    Elimina un item de una tabla dinámica.
    
    Args:
        table_name: Nombre de la tabla
        item_id: ID del item
    
    Returns:
        bool: True si se eliminó correctamente
    """
    if table_name not in DYNAMIC_TABLE_SCHEMAS:
        return False
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id = %s",
            (item_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def clear_patient_dynamic_tables(patient_id):
    """
    Elimina todos los datos de tablas dinámicas para un paciente.
    
    Args:
        patient_id: ID del paciente
    
    Returns:
        bool: True si se completó correctamente
    """
    with get_db_cursor() as (cursor, conn):
        for table_name in DYNAMIC_TABLE_SCHEMAS.keys():
            cursor.execute(
                f"DELETE FROM {table_name} WHERE patient_id = %s",
                (patient_id,)
            )
        conn.commit()
        return True


def save_dynamic_tables_from_dict(patient_id, data_dict, delete_dict=None):
    """
    Guarda tablas dinámicas desde un diccionario de datos.
    
    Estrategia:
    - Si el item tiene 'id', actualizarlo
    - Si no tiene 'id', insertarlo como nuevo
    - Si delete_dict tiene IDs, eliminarlos
    
    Args:
        patient_id: ID del paciente
        data_dict: Diccionario con datos de tablas dinámicas
        delete_dict: Diccionario opcional {tabla: [ids]} para eliminar
    
    Returns:
        bool: True si se completó correctamente
    """
    # Mapeo de categorías a nombres de tabla
    table_mapping = {
        'medicamentos_neurologicos': 'medicamentos_neurologicos',
        'neurologicos': 'medicamentos_neurologicos',
        'medicamentos_hemodinamicos': 'medicamentos_hemodinamicos',
        'hemodinamicos': 'medicamentos_hemodinamicos',
        'medicamentos_nefro': 'medicamentos_nefro',
        'nefro': 'medicamentos_nefro',
        'medicamentos_gastro': 'medicamentos_gastro',
        'gastro': 'medicamentos_gastro',
        'medicacion_hematologica': 'medicacion_hematologica',
        'hematologica': 'medicacion_hematologica',
        'cultivos': 'cultivos',
        'transfusiones': 'transfusiones',
        'antibioticos': 'antibioticos'
    }
    
    with get_db_cursor() as (cursor, conn):
        # Primero eliminar registros marcados para eliminación
        if delete_dict:
            for table_name, ids in delete_dict.items():
                if table_name in DYNAMIC_TABLE_SCHEMAS and ids:
                    for item_id in ids:
                        cursor.execute(
                            f"DELETE FROM {table_name} WHERE id = %s AND patient_id = %s",
                            (item_id, patient_id)
                        )
        
        # Luego procesar inserciones/actualizaciones
        for key, table_name in table_mapping.items():
            if key in data_dict and data_dict[key]:
                items = data_dict[key]
                if isinstance(items, list):
                    for item in items:
                        if not item or not any(v for v in item.values() if v and str(v).strip()):
                            continue
                        
                        valid_columns = DYNAMIC_TABLE_SCHEMAS[table_name]
                        
                        # Si tiene 'id', es actualización
                        if 'id' in item and item['id']:
                            item_id = item['id']
                            filtered_item = {k: v for k, v in item.items() if k in valid_columns and k != 'id' and v is not None}
                            
                            if filtered_item:
                                set_clause = ', '.join([f"{k} = %s" for k in filtered_item.keys()])
                                values = list(filtered_item.values()) + [item_id, patient_id]
                                
                                cursor.execute(
                                    f"UPDATE {table_name} SET {set_clause} WHERE id = %s AND patient_id = %s",
                                    values
                                )
                        else:
                            # Es inserción nueva
                            filtered_item = {k: v for k, v in item.items() if k in valid_columns and v is not None}
                            
                            if filtered_item:
                                columns = ['patient_id'] + list(filtered_item.keys())
                                placeholders = ['%s' for _ in columns]
                                values = [patient_id] + list(filtered_item.values())
                                
                                cursor.execute(
                                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                                    values
                                )
        
        conn.commit()
        return True


# ============================================================================
# EVOLUTION OPERATIONS
# ============================================================================

def create_evolution(patient_id, evolution_data):
    """
    Crea una nueva evolución para un paciente.
    
    Args:
        patient_id: ID del paciente
        evolution_data: Diccionario con datos de evolución
    
    Returns:
        int: ID de la evolución creada
    """
    valid_columns = [
        # Datos básicos
        'fecha', 'hora', 'fc', 'fr', 'tas', 'tad', 'tam', 'temperatura',
        'spo2', 'fio2', 'pafi', 'safio2', 'glasgow', 'rass',
        # Ventilatorio
        'modo_ventilatorio', 'vt_psinp', 'peep', 'ppico', 'pplat',
        'nif', 'driving_pressure', 'compliance', 'p0_1', 'tobin',
        # Química sanguínea
        'glucosa', 'sodio', 'potasio', 'cloro', 'calcio', 'magnesio', 'fosforo',
        'creatinina', 'urea', 'bun',
        # Notas
        'nota', 'plan', 'subjetivo', 'objetivo', 'analisis', 'tipo', 'diagnostico_actual',
        # Balance
        'ingresos', 'egresos', 'diuresis', 'drenajes', 'balance', 'balance_global', 'indice_urinario',
        # Sonda urinaria
        'sonda_urinaria', 'dias_sonda_urinaria', 'fecha_colocacion_sonda_urinaria', 'fecha_retiro_sonda_urinaria',
        # Dispositivos invasivos adicionales
        'cateter_cvc', 'dias_cvc', 'fecha_colocacion_cvc', 'fecha_retiro_cvc',
        'sonda_endopleural', 'dias_endopleural', 'fecha_colocacion_endopleural', 'fecha_retiro_endopleural',
        'sonda_nasogastrica', 'dias_sng', 'fecha_colocacion_sng', 'fecha_retiro_sng',
        'tubo_endotraqueal', 'dias_ett', 'fecha_colocacion_ett', 'fecha_retiro_ett',
        # Dispositivos nuevos
        'traqueostomia', 'dias_traqueostomia', 'fecha_colocacion_traqueostomia', 'fecha_retiro_traqueostomia',
        'cateter_intraventricular', 'dias_cateter_intraventricular', 'fecha_colocacion_cateter_intraventricular', 'fecha_retiro_cateter_intraventricular',
        'gastrostomia', 'dias_gastrostomia', 'fecha_colocacion_gastrostomia', 'fecha_retiro_gastrostomia',
        'linea_arterial', 'dias_linea_arterial', 'fecha_colocacion_linea_arterial', 'fecha_retiro_linea_arterial',
        # Catéter de hemodiálisis
        'cateter_hemodialisis', 'dias_hemodialisis', 'fecha_colocacion_hemodialisis', 'fecha_retiro_hemodialisis',
        # Hematología
        'hemoglobina', 'hematocrito', 'leucocitos', 'neutrofilos', 'linfocitos', 'plaquetas',
        # Gasometría
        'ph', 'pco2', 'po2', 'hco3', 'lactato',
        # Inflamación
        'pcr', 'pct', 'vsg',
        # Coagulación
        'tp', 'ttp', 'inr', 'fibrinogeno', 'dimero_d',
        # Marcadores cardíacos
        'troponina', 'bnp',
        # Función hepática
        'bilirrubina_total', 'bilirrubina_directa', 'bilirrubina_indirecta',
        'albumina', 'alt', 'ast', 'dhl', 'fosfatasa_alcalina', 'amilasa', 'lipasa',
        # Imagen y EKG
        'imagen_estudios', 'ekg_texto',
        # Resumen de tratamiento
        'cultivos_resumen', 'antibioticos_resumen'
    ]
    
    filtered_data = {k: v for k, v in evolution_data.items() if k in valid_columns}
    
    if not filtered_data:
        return None
    
    columns = ['patient_id'] + list(filtered_data.keys())
    placeholders = ['%s' for _ in columns]
    values = [patient_id] + list(filtered_data.values())
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"INSERT INTO evoluciones ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id",
            values
        )
        evolution_id = cursor.fetchone()[0]
        conn.commit()
        return evolution_id


def get_evolutions(patient_id, limit=None):
    """
    Obtiene las evoluciones de un paciente.
    
    Args:
        patient_id: ID del paciente (int o str)
        limit: Límite de registros (opcional)
    
    Returns:
        list: Lista de diccionarios con evoluciones
    """
    # Convertir a string ya que patient_id en evoluciones es VARCHAR
    patient_id_str = str(patient_id)
    
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        if limit:
            cursor.execute(
                """SELECT * FROM evoluciones 
                   WHERE patient_id = %s 
                   ORDER BY fecha DESC, hora DESC NULLS LAST
                   LIMIT %s""",
                (patient_id_str, limit)
            )
        else:
            cursor.execute(
                """SELECT * FROM evoluciones 
                   WHERE patient_id = %s 
                   ORDER BY fecha DESC, hora DESC NULLS LAST""",
                (patient_id_str,)
            )
        
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def get_evolution(evolution_id):
    """
    Obtiene una evolución específica.
    
    Args:
        evolution_id: ID de la evolución
    
    Returns:
        dict: Datos de la evolución o None
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT * FROM evoluciones WHERE id = %s",
            (evolution_id,)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def get_ingreso_evolution(patient_id):
    """
    Obtiene la evolución de ingreso (la primera evolución) de un paciente.
    
    Args:
        patient_id: ID del paciente
    
    Returns:
        dict: Datos de la evolución de ingreso o None
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT * FROM evoluciones WHERE patient_id = %s AND tipo = 'ingreso' ORDER BY created_at ASC LIMIT 1",
            (patient_id,)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def update_evolution(evolution_id, evolution_data):
    """
    Actualiza una evolución.
    
    Args:
        evolution_id: ID de la evolución
        evolution_data: Diccionario con datos a actualizar
    
    Returns:
        bool: True si se actualizó correctamente
    """
    valid_columns = [
        # Datos básicos
        'fecha', 'hora', 'fc', 'fr', 'tas', 'tad', 'tam', 'temperatura',
        'spo2', 'fio2', 'pafi', 'safio2', 'glasgow', 'rass',
        # Ventilatorio
        'modo_ventilatorio', 'vt_psinp', 'peep', 'ppico', 'pplat',
        'nif', 'driving_pressure', 'compliance', 'p0_1', 'tobin',
        # Química sanguínea
        'glucosa', 'sodio', 'potasio', 'cloro', 'calcio', 'magnesio', 'fosforo',
        'creatinina', 'urea', 'bun',
        # Notas
        'nota', 'plan', 'subjetivo', 'objetivo', 'analisis', 'tipo', 'diagnostico_actual',
        # Balance
        'ingresos', 'egresos', 'diuresis', 'drenajes', 'balance', 'balance_global', 'indice_urinario',
        # Sonda urinaria
        'sonda_urinaria', 'dias_sonda_urinaria', 'fecha_colocacion_sonda_urinaria', 'fecha_retiro_sonda_urinaria',
        # Dispositivos invasivos adicionales
        'cateter_cvc', 'dias_cvc', 'fecha_colocacion_cvc', 'fecha_retiro_cvc',
        'sonda_endopleural', 'dias_endopleural', 'fecha_colocacion_endopleural', 'fecha_retiro_endopleural',
        'sonda_nasogastrica', 'dias_sng', 'fecha_colocacion_sng', 'fecha_retiro_sng',
        'tubo_endotraqueal', 'dias_ett', 'fecha_colocacion_ett', 'fecha_retiro_ett',
        # Dispositivos nuevos
        'traqueostomia', 'dias_traqueostomia', 'fecha_colocacion_traqueostomia', 'fecha_retiro_traqueostomia',
        'cateter_intraventricular', 'dias_cateter_intraventricular', 'fecha_colocacion_cateter_intraventricular', 'fecha_retiro_cateter_intraventricular',
        'gastrostomia', 'dias_gastrostomia', 'fecha_colocacion_gastrostomia', 'fecha_retiro_gastrostomia',
        'linea_arterial', 'dias_linea_arterial', 'fecha_colocacion_linea_arterial', 'fecha_retiro_linea_arterial',
        # Catéter de hemodiálisis
        'cateter_hemodialisis', 'dias_hemodialisis', 'fecha_colocacion_hemodialisis', 'fecha_retiro_hemodialisis',
        # Hematología
        'hemoglobina', 'hematocrito', 'leucocitos', 'neutrofilos', 'linfocitos', 'plaquetas',
        # Gasometría
        'ph', 'pco2', 'po2', 'hco3', 'lactato',
        # Inflamación
        'pcr', 'pct', 'vsg',
        # Coagulación
        'tp', 'ttp', 'inr', 'fibrinogeno', 'dimero_d',
        # Marcadores cardíacos
        'troponina', 'bnp',
        # Función hepática
        'bilirrubina_total', 'bilirrubina_directa', 'bilirrubina_indirecta',
        'albumina', 'alt', 'ast', 'dhl', 'fosfatasa_alcalina', 'amilasa', 'lipasa',
        # Imagen y EKG
        'imagen_estudios', 'ekg_texto',
        # Resumen de tratamiento
        'cultivos_resumen', 'antibioticos_resumen'
    ]
    
    filtered_data = {k: v for k, v in evolution_data.items() 
                     if k in valid_columns and v is not None}
    
    if not filtered_data:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered_data.keys()])
    values = list(filtered_data.values()) + [evolution_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"UPDATE evoluciones SET {set_clause} WHERE id = %s",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_evolution(evolution_id):
    """
    Elimina una evolución.
    
    Args:
        evolution_id: ID de la evolución
    
    Returns:
        bool: True si se eliminó correctamente
    """
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "DELETE FROM evoluciones WHERE id = %s",
            (evolution_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# CLINICAL NOTES OPERATIONS
# ============================================================================

def create_clinical_note(patient_id, template_type, title, content):
    """
    Crea una nota clínica.
    
    Args:
        patient_id: ID del paciente
        template_type: Tipo de template usado
        title: Título de la nota
        content: Contenido de la nota
    
    Returns:
        int: ID de la nota creada
    """
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            """INSERT INTO clinical_notes (patient_id, template_type, title, content) 
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (patient_id, template_type, title, content)
        )
        note_id = cursor.fetchone()[0]
        conn.commit()
        return note_id


def get_clinical_notes(patient_id):
    """
    Obtiene las notas clínicas de un paciente.
    
    Args:
        patient_id: ID del paciente
    
    Returns:
        list: Lista de diccionarios con notas
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            """SELECT * FROM clinical_notes 
               WHERE patient_id = %s 
               ORDER BY created_at DESC""",
            (patient_id,)
        )
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def get_clinical_note(note_id):
    """
    Obtiene una nota clínica específica.
    
    Args:
        note_id: ID de la nota
    
    Returns:
        dict: Datos de la nota o None
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT * FROM clinical_notes WHERE id = %s",
            (note_id,)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


# ============================================================================
# SNAPSHOT OPERATIONS
# ============================================================================

def create_snapshot(patient_id, snapshot_data):
    """
    Crea un snapshot clínico.
    
    Args:
        patient_id: ID del paciente
        snapshot_data: Diccionario con datos del snapshot
    
    Returns:
        int: ID del snapshot creado
    """
    valid_columns = [
        'glasgow', 'rass', 'cpot', 'tas', 'tad', 'pam', 'fc', 'fr', 
        'spo2', 'fio2', 'pafi', 'creatinina', 'bun', 'diuresis',
        'leucocitos', 'plaquetas', 'hemoglobina'
    ]
    
    filtered_data = {k: v for k, v in snapshot_data.items() if k in valid_columns}
    
    if not filtered_data:
        return None
    
    columns = ['patient_id'] + list(filtered_data.keys())
    placeholders = ['%s' for _ in columns]
    values = [patient_id] + list(filtered_data.values())
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            f"INSERT INTO clinical_snapshots ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id",
            values
        )
        snapshot_id = cursor.fetchone()[0]
        conn.commit()
        return snapshot_id


def get_snapshots(patient_id, start_date=None, end_date=None):
    """
    Obtiene los snapshots de un paciente.
    
    Args:
        patient_id: ID del paciente
        start_date: Fecha inicial (opcional)
        end_date: Fecha final (opcional)
    
    Returns:
        list: Lista de diccionarios con snapshots
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        if start_date and end_date:
            cursor.execute(
                """SELECT * FROM clinical_snapshots 
                   WHERE patient_id = %s 
                   AND snapshot_date BETWEEN %s AND %s
                   ORDER BY snapshot_date""",
                (patient_id, start_date, end_date)
            )
        else:
            cursor.execute(
                """SELECT * FROM clinical_snapshots 
                   WHERE patient_id = %s 
                   ORDER BY snapshot_date""",
                (patient_id,)
            )
        
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


# ============================================================================
# TEXTO LIBRE EN EVOLUCIONES (Tabla simple para notas adicionales)
# ============================================================================

def create_texto_libre(evolution_id, patient_id, contenido):
    """
    Crea o actualiza el texto libre de una evolucion.
    Como es 1:1 con evolucion, hace UPSERT.
    
    Args:
        evolution_id: ID de la evolucion
        patient_id: ID del paciente
        contenido: Texto libre
    
    Returns:
        bool: True si se guardo correctamente
    """
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            """INSERT INTO evolucion_texto_libre (evolution_id, patient_id, contenido, updated_at)
               VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
               ON CONFLICT (evolution_id) DO UPDATE SET
                   contenido = EXCLUDED.contenido,
                   updated_at = CURRENT_TIMESTAMP
            """,
            (evolution_id, patient_id, contenido)
        )
        conn.commit()
        return True


def get_texto_libre(evolution_id):
    """
    Obtiene el texto libre de una evolucion.
    
    Args:
        evolution_id: ID de la evolucion
    
    Returns:
        str: Contenido del texto libre o cadena vacia
    """
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute(
            "SELECT contenido FROM evolucion_texto_libre WHERE evolution_id = %s",
            (evolution_id,)
        )
        row = cursor.fetchone()
        if row and row['contenido']:
            return row['contenido']
        return ""


def delete_texto_libre(evolution_id):
    """
    Elimina el texto libre de una evolucion.
    
    Args:
        evolution_id: ID de la evolucion
    
    Returns:
        bool: True si se elimino correctamente
    """
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "DELETE FROM evolucion_texto_libre WHERE evolution_id = %s",
            (evolution_id,)
        )
        conn.commit()
        return True

