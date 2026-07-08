"""
SINAPSID DMA - Generador de Notas Clínicas
==========================================
Generador de notas médicas basado en templates.
Basado en clinical_manager_audit.md
"""

from datetime import datetime, date


class ClinicalNoteGenerator:
    """Generador de notas clínicas a partir de templates."""
    
    TEMPLATES = {
        'nota_ingreso_uci': {
            'titulo': 'Nota de Ingreso a UCI',
            'contenido': '''Nota de ingreso a unidad de cuidados intensivos.

Datos generales:
Paciente: {nombre_completo}
Edad: {edad} años
Sexo: {sexo}
Expediente: {expediente}
CURP: {curp}
Episodio: {episodio}
Cama: {cama}
Fecha de ingreso al hospital: {fecha_ingreso_hosp}
Fecha de ingreso a UCIA: {fecha_ingreso}
Días de estancia: {dias_estancia}

Exploración física:

Neurológico:
CPOT: {cpot}, RASS: {rass}, Glasgow: {glasgow}
Reflejos: pupilar {reflejo_pupilar}, corneal {reflejo_corneal}, tusígeno {reflejo_tusigeno}
ROTs: {rots}
Tamaño pupilas: {pupilas_mm} mm
Exploración neurológica: {exploracion_neurologica}
Imagen neurológica: {imagen_neurologica}

Hemodinámico:
Mottling: {mottling}, llenado capilar: {llenado_capilar} s
TA: {tas}/{tad} (TAM {tam} mmHg), FC: {fc} lpm
EKG: {ekg}
Exploración hemodinámica: {exploracion_hemodinamica}

Ventilatorio:
Talla: {talla} m, peso ideal: {peso_ideal} kg
FR: {fr} rpm, SatO2: {sao2}%, FiO2: {fio2}%
Modo ventilatorio: {modo_ventilatorio}
Fecha inicio VM: {inicio_ventilador}
Traqueostomía ingreso: {traqueostomia_ingreso}
Número tubo: {numero_tubo}, arcada: {arcada} cm
VT/PSinP: {vt_psinp}, VT/peso: {vt_peso} mL/kg
PEEP: {peep}, Relación I:E: {relacion_ie}
Ppico: {ppico}, Pplat: {pplat}, Driving pressure: {driving_pressure}
Vol min: {vol_min}, P0.1: {p0_1}, NIF: {nif}, TOS: {tos}
Exploración ventilatoria: {exploracion_ventilatoria}
Imagen ventilatoria: {imagen_ventilatoria}
Protocolo BLUE: {blue}
Gasometría ({gasometria_fecha}): pH {gasometria_ph}, PCO2 {gasometria_pco2}, PO2 {gasometria_po2}, HCO3 {gasometria_hco3}, Lactato {gasometria_lactato}
Índice Tobin: {tobin}, PaFiO2: {pafi}
Otros: {vent_otros}

Hídrico y Renal:
Sonda vesical: {sonda_vesical}
Peso estimado: {peso_estimado} kg
Diuresis total: {diuresis_total} mL (Periodo: {periodo_horas} h), índice urinario: {indice_urinario} mL/kg/h
Ingresos: {ingresos} mL, egresos: {egresos} mL, balance: {balance} mL, balance global: {balance_global}
BUN: {bun}, urea: {urea}, creatinina: {creatinina}
Electrolitos: Na {sodio}, K {potasio}, Cl {cloro}, P {fosforo}, Mg {magnesio}, Ca {calcio}
EGO: {ego}
TFG: {tfg}, Osmolaridad: {osmolaridad}

Gastrometabólico:
IMC: {imc}, peso ajustado: {peso_ajustado}
Ayuno: {ayuno}, gastrostomía: {gastrostomia_ingreso}
Sonda Levin: {sonda_levin}
Proteínas requeridas: {proteinas_requeridas} g/día
Tipo nutrición: {tipo_nutricion} Producto: {producto_nutricion}
Volumen aporte: {ml_24h_calc} mL/24h, kcal aporte: {kcal_aporte}, proteínas aporte: {proteinas_aporte}
Glucemia capilar: {glucemia_capilar}
Insulina glargina: {insulina_glargina} U/24h, insulina rápida: {insulina_rapida} U/24h
Evacuaciones: {evacuaciones}, Bristol: {bristol}
Glucosa central: {glucosa_central}
Albúmina: {albumina}
Exploración gastrometabólica: {exploracion_gastro}
Drenajes: {drenajes}

Hematológico e Infeccioso:
Temperatura: {temperatura} °C
Leucocitos: {leucocitos}, neutrófilos: {neutrofilos}, linfocitos: {linfocitos}
Hb: {hemoglobina} g/dL, Hto: {hematocrito}%, plaquetas: {plaquetas}
TP: {tp}, TTP: {ttp}, INR: {inr}
Exploración hematológica: {exploracion_hema}

Diagnóstico(s) de ingreso:
{diagnostico_ingreso}

Plan:
{plan_ingreso}

ESCALAS PRONÓSTICAS:
NEWS2: {news2_ingreso} - {news2_interpretado}
SOFA II: {sofa2_ingreso} (Mortalidad aproximada {sofa_mortalidad})
APACHE II: {apache2_ingreso} - {apache2_mortalidad}
SAPS3: {saps3_ingreso} - {saps3_mortalidad}
SWIFT Score: {swift_score}
'''
        },
        'nota_evolucion_psoap': {
            'titulo': 'Nota de Evolución PSOAP',
            'contenido': '''NOTA DE EVOLUCIÓN UNIDAD DE CUIDADOS INTENSIVOS ADULTOS

PACIENTE:
Nombre: {nombre_completo}
Edad: {edad} AÑOS
Sexo: {sexo}
Expediente: {expediente}
CURP: {curp}
Episodio: {episodio}
Cama: {cama}
Fecha de ingreso al hospital: {fecha_ingreso_hosp}
Fecha de ingreso a UCIA: {fecha_ingreso}
DÍAS DE ESTANCIA: {dias_estancia}

DIAGNÓSTICOS:
{diagnostico_ingreso}

/   /   /   /

SUBJETIVO:
{subjetivo}

/   /   /   /

OBJETIVO:

SIGNOS VITALES: Glasgow {glasgow} PTS, TA {tas}/{tad} MMHG (TAM {tam}), FC {fc} LPM, FR {fr} RPM, SPO2 {sao2}%, TEMP {temperatura} °C, GLUC {glucosa} MG/DL, PESO {peso_estimado} KG, TALLA {talla} M
PA/FIO2 {pafi}

EXPLORACION FISICA:
{exploracion_fisica}

BALANCE HIDRICO:
DIURESIS TOTAL: {diuresis_total} ML ({indice_urinario} ML/KG/H)
INGRESOS: {ingresos} ML
EGRESOS: {egresos} ML
BALANCE GLOBAL: {balance_global} ML

LABORATORIOS:
{laboratorios_text}

/   /   /   /

ANALISIS:
{evaluacion}

/   /   /   /

PLAN:
{plan}

PACIENTE {estado_salud}, PRONOSTICO {pronostico}, FAMILIARES INFORMADOS.

ESCALAS PRONÓSTICAS:
SOFA: {sofa} (MORTALIDAD {mortalidad_sofa})
SOFA II: {sofa2} PUNTOS (MORTALIDAD {mortalidad_sofa2})
APACHE II: {apache2} (MORTALIDAD {mortalidad_apache2})
SAPS 3: {saps3} (MORTALIDAD {mortalidad_saps3})
SWIFT: {swift}
'''
        },
        'nota_egreso': {
            'titulo': 'Nota de Egreso UCI',
            'contenido': '''NOTA DE EGRESO - UNIDAD DE CUIDADOS INTENSIVOS ADULTOS

PACIENTE:
Nombre: {nombre_completo}
Edad: {edad} AÑOS
Sexo: {sexo}
Expediente: {expediente}
CURP: {curp}
Episodio: {episodio}
Cama: {cama}
Fecha de ingreso a UCIA: {fecha_ingreso}
Fecha de egreso de UCIA: {fecha_egreso_uci}
Fecha de egreso del hospital: {fecha_egreso_hospital}
DÍAS DE ESTANCIA UCI: {dias_estancia}

DIAGNÓSTICO(S) DE INGRESO:
{diagnostico_ingreso}

DIAGNÓSTICO(S) DE EGRESO:
{diagnostico_egreso}

/   /   /   /

RESUMEN DE ESTANCIA:

El paciente permaneció en la Unidad de Cuidados Intensivos Adultos por {dias_estancia} días.

AL EGRESO:

SIGNOS VITALES: FC {fc_egreso} LPM, FR {fr_egreso} RPM, TA {tas_egreso}/{tad_egreso} MMHG (TAM {tam_egreso}), SPO2 {sao2_egreso}% CON FI02 {fio2_egreso}%, TEMP {temperatura_egreso} °C

LABORATORIOS AL EGRESO:
Hb: {hemoglobina_egreso} g/dL, Hto: {hematocrito_egreso}%, Leucocitos: {leucocitos_egreso}, Plaquetas: {plaquetas_egreso}
Neutrófilos: {neutrofilos_egreso}%, Linfocitos: {linfocitos_egreso}%
PCR: {pcr_egreso}, PCT: {pct_egreso}
Na: {sodio_egreso}, K: {potasio_egreso}, Cl: {cloro_egreso}
Creatinina: {creatinina_egreso}, BUN: {bun_egreso}, Urea: {urea_egreso}
Glucosa: {glucosa_egreso}
Bilirrubina total: {bilirrubina_total_egreso}, Directa: {bilirrubina_directa_egreso}, Albúmina: {albumina_egreso}
Gasometría: pH {gasometria_ph_egreso}, PCO2 {gasometria_pco2_egreso}, PO2 {gasometria_po2_egreso}, HCO3 {gasometria_hco3_egreso}, Lactato {gasometria_lactato_egreso}

ESTADO AL EGRESO:
{tipo_egreso}

Servicio de destino: {servicio_egreso}

PRONÓSTICO AL EGRESO: {pronostico_egreso}

FAMILIARES INFORMADOS.

ESCALAS PRONÓSTICAS AL INGRESO:
NEWS2: {news2_ingreso}
SOFA II: {sofa2_ingreso}
APACHE II: {apache2_ingreso} - {apache2_mortalidad}
SAPS3: {saps3_ingreso} - {saps3_mortalidad}
'''
        },
        'nota_medica_simple': {
            'titulo': 'Nota Médica',
            'contenido': '''Nota de Evolución

Fecha: {fecha_actual}
Paciente: {nombre_completo}, {edad} años, {sexo}
Ingreso: {fecha_ingreso}, días de estancia: {dias_estancia}

Neurológico: Glasgow {glasgow}, RASS {rass}, CPOT {cpot}
Hemodinámico: TAM {tam} mmHg, FC {fc} lpm
Ventilatorio: Modo {modo_ventilatorio}, FiO2 {fio2}%, PEEP {peep}
Renal: Diuresis {diuresis_total} mL/24h, creatinina {creatinina}
Gastrometabólico: Glucemia {glucemia_capilar} mg/dL, nutrición {tipo_nutricion}
Infeccioso: Temperatura {temperatura} °C, leucocitos {leucocitos}, PCR {pcr}

Diagnóstico: {diagnostico_ingreso}

Plan: {plan_ingreso}
'''
        },
        'resumen_datos': {
            'titulo': 'Resumen de Datos',
            'contenido': '''{__raw__}'''
        }
    }
    
    def get_templates(self):
        """Retorna la lista de templates disponibles."""
        return [
            {'id': key, 'titulo': value['titulo']}
            for key, value in self.TEMPLATES.items()
        ]
    
    def get_template(self, template_id):
        """Retorna un template específico."""
        return self.TEMPLATES.get(template_id)
    
    def generate(self, template_id, patient_data):
        """
        Genera una nota a partir de un template.
        
        Args:
            template_id: ID del template
            patient_data: Diccionario con datos del paciente
        
        Returns:
            str: Nota generada
        """
        template = self.get_template(template_id)
        if not template:
            return f"Template '{template_id}' no encontrado"
        
        # Agregar fecha actual si no está presente
        if 'fecha_actual' not in patient_data:
            patient_data['fecha_actual'] = date.today().strftime('%d/%m/%Y')
        
        # Procesar variables dinámicas (tablas)
        data = self._process_dynamic_data(patient_data)
        
        # Generar texto de laboratorios si no está presente
        if 'laboratorios_text' not in data:
            data['laboratorios_text'] = self._generate_labs_text(data)
        
        # Generar subjetivo por defecto si no está presente
        if 'subjetivo' not in data or not data['subjetivo']:
            data['subjetivo'] = 'Sin síntomas reportados'
        
        # Generar exploración física por defecto
        if 'exploracion_fisica' not in data or not data['exploracion_fisica']:
            data['exploracion_fisica'] = 'Sin alteraciones significativas'
        
        # Generar evaluación por defecto
        if 'evaluacion' not in data or not data['evaluacion']:
            data['evaluacion'] = 'Paciente estable'
        
        # Generar plan por defecto
        if 'plan' not in data or not data['plan']:
            data['plan'] = 'Continuar manejo actual'
        
        # Estado de salud y pronóstico por defecto
        if 'estado_salud' not in data:
            data['estado_salud'] = 'ESTABLE'
        if 'pronostico' not in data:
            data['pronostico'] = 'RESERVADO'
        
        try:
            # Formatear el template con los datos
            # Usar defaultdict para evitar errores por variables faltantes
            from collections import defaultdict
            safe_data = defaultdict(str, data)
            
            if template_id == 'resumen_datos':
                return self._generate_raw_dump(data)
            
            return template['contenido'].format_map(safe_data)
        except KeyError as e:
            return f"Error: Variable no encontrada {e}. Nota generada parcialmente:\n\n{template['contenido']}"
    
    def _process_dynamic_data(self, data):
        """Procesa los datos dinámicos (tablas) del paciente."""
        result = data.copy()
        
        # === MAPEO DE CAMPOS PSOAP ===
        # El formulario envía: objetivo, analisis, plan_nota
        # El template espera: exploracion_fisica, evaluacion, plan
        field_map = {
            "objetivo": "exploracion_fisica",
            "analisis": "evaluacion",
            "plan_nota": "plan",
        }
        for source_field, target_field in field_map.items():
            if source_field in result and result[source_field]:
                result[target_field] = result[source_field]
        
        # Procesar medicamentos neurológicos
        if 'medicamentos_neurologicos' in data and isinstance(data['medicamentos_neurologicos'], list):
            result['medicamentos_neurologicos'] = self._format_table(
                data['medicamentos_neurologicos'],
                ['Medicamento', 'Unidad', 'Dosis', 'Fecha inicio', 'Fecha fin', 'Indicación']
            )
        
        # Procesar medicamentos hemodinámicos
        if 'medicamentos_hemodinamicos' in data and isinstance(data['medicamentos_hemodinamicos'], list):
            result['medicamentos_hemodinamicos'] = self._format_table(
                data['medicamentos_hemodinamicos'],
                ['Medicamento', 'Unidad', 'Dosis máx', 'Dosis mín', 'Fecha inicio', 'Fecha fin', 'Indicación']
            )
        
        # Procesar medicamentos nefro
        if 'medicamentos_nefro' in data and isinstance(data['medicamentos_nefro'], list):
            result['medicamentos_nefro'] = self._format_table(
                data['medicamentos_nefro'],
                ['Medicamento', 'Unidad', 'Dosis', 'Fecha inicio', 'Fecha fin']
            )
        
        # Procesar medicamentos gastro
        if 'medicamentos_gastro' in data and isinstance(data['medicamentos_gastro'], list):
            result['medicamentos_gastro'] = self._format_table(
                data['medicamentos_gastro'],
                ['Medicamento', 'Unidad', 'Dosis', 'Fecha inicio', 'Fecha fin']
            )
        
        # Procesar medicación hematológica
        if 'medicacion_hematologica' in data and isinstance(data['medicacion_hematologica'], list):
            result['medicacion_hematologica'] = self._format_table(
                data['medicacion_hematologica'],
                ['Medicamento', 'Dosis', 'Unidad', 'Fecha inicio', 'Fecha fin', 'Indicación']
            )
        
        # Procesar cultivos
        if 'cultivos' in data and isinstance(data['cultivos'], list):
            result['cultivos'] = self._format_table(
                data['cultivos'],
                ['Tipo', 'Fecha', 'Resultado', 'Sensibilidad', 'Resistencia']
            )
        
        # Procesar transfusiones
        if 'transfusiones' in data and isinstance(data['transfusiones'], list):
            result['transfusiones'] = self._format_table(
                data['transfusiones'],
                ['Componente', 'Dosis (U)', 'Dosis (mL)', 'Fecha', 'Reacción']
            )
        
        # Convertir booleanos a texto
        for key, value in result.items():
            if isinstance(value, bool):
                result[key] = 'Sí' if value else 'No'
        
        return result
    
    def _format_table(self, rows, columns):
        """Formatea una tabla como texto legible."""
        if not rows:
            return 'Ninguno'
        
        lines = []
        for i, row in enumerate(rows, 1):
            if isinstance(row, dict):
                item_text = f"{i}. "
                parts = []
                for col in columns:
                    key = col.lower().replace(' ', '_').replace('(', '').replace(')', '')
                    if key in row and row[key]:
                        parts.append(f"{col}: {row[key]}")
                if parts:
                    item_text += ", ".join(parts)
                    lines.append(item_text)
        
        return "\n".join(lines) if lines else 'Ninguno'
    
    def _generate_labs_text(self, data):
        """Genera texto de laboratorios a partir de los datos."""
        lab_keys = [
            'hemoglobina', 'hematocrito', 'plaquetas', 'leucocitos',
            'neutrofilos', 'linfocitos', 'glucosa', 'urea', 'bun', 'creatinina',
            'sodio', 'potasio', 'cloro', 'fosforo', 'magnesio', 'calcio',
            'gasometria_ph', 'gasometria_pco2', 'gasometria_po2', 
            'gasometria_hco3', 'gasometria_lactato', 'pcr', 'pct'
        ]
        
        lines = []
        for key in lab_keys:
            value = data.get(key)
            if value is not None:
                # Formatear nombre
                nombre = key.replace('gasometria_', '').replace('_', ' ').upper()
                lines.append(f"{nombre}: {value}")
        
        return "\n".join(lines) if lines else 'No se ingresaron laboratorios'
    
    def _generate_raw_dump(self, data):
        """Genera un volcado crudo de datos."""
        lines = ['=== RESUMEN DE DATOS DEL PACIENTE ===', '']
        
        for key, value in sorted(data.items()):
            if value is not None and value != '':
                if isinstance(value, list):
                    lines.append(f"{key}: {len(value)} items")
                elif isinstance(value, dict):
                    lines.append(f"{key}: {len(value)} campos")
                else:
                    lines.append(f"{key}: {value}")
        
        return "\n".join(lines)


# Instancia global del generador
note_generator = ClinicalNoteGenerator()


def get_note_generator():
    """Retorna la instancia del generador de notas."""
    return note_generator
