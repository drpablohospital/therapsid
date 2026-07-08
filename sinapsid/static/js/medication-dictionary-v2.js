/**
 * Diccionario de Medicamentos v2.0
 * - Todo en MAYÚSCULAS sin acentos
 * - Incluye vías de administración
 * - Unidades según vía (BIC, IV, SC, SNG, ORAL, OTRA)
 */

const MEDICATION_DICTIONARY_V2 = {
    // VÍAS DE ADMINISTRACIÓN Y SUS UNIDADES
    vias: {
        'BIC': {
            label: 'BIC (BOLO INTERMITENTE CONTINUO)',
            unidades: ['MG/KG/D', 'MG/KG/H', 'MCG/KG/MIN', 'DU', 'UI/KG/D', 'UI/KG/H'],
            es_infusion: true
        },
        'IV': {
            label: 'IV (INTRAVENOSA)',
            unidades: ['MG', 'G', 'UI', 'MCG', 'ML', 'MG/KG', 'UI/KG', 'MG/KG/D', 'MG/KG/H'],
            es_infusion: false
        },
        'SC': {
            label: 'SC (SUBCUTANEA)',
            unidades: ['MG', 'UI', 'MCG', 'ML', 'UI/KG'],
            es_infusion: false
        },
        'SNG': {
            label: 'SNG (SONDA NASOGASTRICA)',
            unidades: ['MG', 'G', 'ML', 'UI', 'MG/KG', 'UI/KG'],
            es_infusion: false
        },
        'ORAL': {
            label: 'ORAL',
            unidades: ['MG', 'G', 'ML', 'UI', 'MG/KG', 'UI/KG', 'COMPRIMIDOS', 'CÁPSULAS'],
            es_infusion: false
        },
        'OTRA': {
            label: 'OTRA',
            unidades: ['MG', 'G', 'UI', 'MCG', 'ML', 'UNIDADES', 'AMPOLLAS', 'FRASCOS'],
            es_infusion: false
        }
    },

    // FRECUENCIAS DE ADMINISTRACIÓN
    frecuencias: [
        { value: '1D', label: '1D (CADA 24 HORAS)', horas: 24 },
        { value: '2D', label: '2D (CADA 12 HORAS)', horas: 12 },
        { value: '3D', label: '3D (CADA 8 HORAS)', horas: 8 },
        { value: '4D', label: '4D (CADA 6 HORAS)', horas: 6 },
        { value: '6D', label: '6D (CADA 4 HORAS)', horas: 4 },
        { value: '8D', label: '8D (CADA 3 HORAS)', horas: 3 },
        { value: 'CONTINUO', label: 'CONTINUO (INFUSIÓN)', horas: 0 },
        { value: 'PRN', label: 'PRN (SEGÚN NECESIDAD)', horas: null },
        { value: 'UNICA', label: 'DOSIS ÚNICA', horas: null }
    ],

    // MEDICAMENTOS NEUROLÓGICOS
    neurologicos: {
        'MIDAZOLAM': { 
            vias_permitidas: ['IV', 'BIC', 'IM'],
            dosis: { 'IV': '0.05-0.2 MG/KG', 'BIC': '0.1-0.3 MG/KG/H', 'IM': '0.07-0.15 MG/KG' },
            indicacion: 'SEDACION'
        },
        'PROPOFOL': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '5-50 MCG/KG/MIN', 'BIC': '0.3-4 MG/KG/H' },
            indicacion: 'SEDACION/ANESTESIA'
        },
        'FENTANILO': { 
            vias_permitidas: ['IV', 'BIC', 'EPIDURAL'],
            dosis: { 'IV': '25-100 MCG/H', 'BIC': '0.5-2 MCG/KG/H' },
            indicacion: 'ANALGESIA'
        },
        'MORFINA': { 
            vias_permitidas: ['IV', 'BIC', 'SC', 'EPIDURAL'],
            dosis: { 'IV': '2-10 MG/H', 'BIC': '0.5-2 MG/KG/D', 'SC': '5-20 MG/4-6H' },
            indicacion: 'DOLOR AGUDO'
        },
        'DEXMEDETOMIDINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.2-0.7 MCG/KG/H', 'BIC': '0.2-0.7 MCG/KG/H' },
            indicacion: 'SEDACION'
        },
        'KETAMINA': { 
            vias_permitidas: ['IV', 'BIC', 'IM'],
            dosis: { 'IV': '0.1-0.5 MG/KG/H', 'BIC': '0.1-0.5 MG/KG/H', 'IM': '2-4 MG/KG' },
            indicacion: 'ANALGESIA/SEDACION'
        },
        'LEVETIRACETAM': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '500-1500 MG/12H', 'BIC': '500-1500 MG/12H' },
            indicacion: 'ANTIEPILEPTICO'
        },
        'FENITOINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '100-300 MG/D', 'BIC': '15-20 MG/KG/D' },
            indicacion: 'CRISIS CONVULSIVAS'
        },
        'VALPROATO': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '500-1500 MG/8H', 'BIC': '500-1500 MG/8H' },
            indicacion: 'ANTIEPILEPTICO'
        },
        'MANITOL': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.25-1 G/KG', 'BIC': '0.25-1 G/KG/4-6H' },
            indicacion: 'EDEMA CEREBRAL'
        },
        'FUROSEMIDA': { 
            vias_permitidas: ['IV', 'BIC', 'IM', 'ORAL'],
            dosis: { 'IV': '20-200 MG', 'BIC': '0.5-1 MG/KG/D', 'IM': '20-40 MG', 'ORAL': '20-80 MG' },
            indicacion: 'EDEMA CEREBRAL/HIPEOSMOLAR'
        },
        'HALOPERIDOL': { 
            vias_permitidas: ['IV', 'IM', 'ORAL'],
            dosis: { 'IV': '2-10 MG/8H', 'IM': '2-5 MG/8H', 'ORAL': '2-10 MG/8H' },
            indicacion: 'DELIRIUM'
        },
        'QUETIAPINA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '25-200 MG/12H', 'SNG': '25-200 MG/12H' },
            indicacion: 'DELIRIUM/PSI'
        },
        'OLANZAPINA': { 
            vias_permitidas: ['IM', 'ORAL', 'SNG'],
            dosis: { 'IM': '2.5-10 MG', 'ORAL': '2.5-10 MG/24H', 'SNG': '2.5-10 MG/24H' },
            indicacion: 'DELIRIUM/AGITACION'
        },
        'LORAZEPAM': { 
            vias_permitidas: ['IV', 'IM', 'ORAL'],
            dosis: { 'IV': '1-4 MG/4-6H', 'IM': '1-4 MG/4-6H', 'ORAL': '1-4 MG/4-6H' },
            indicacion: 'ANSIEDAD/CONVULSIONES'
        },
        'DIAZEPAM': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'RECTAL'],
            dosis: { 'IV': '5-10 MG', 'IM': '5-10 MG', 'ORAL': '5-10 MG/6-8H', 'RECTAL': '10-20 MG' },
            indicacion: 'STATUS EPILEPTICO'
        }
    },

    // MEDICAMENTOS HEMODINÁMICOS
    hemodinamicos: {
        'NORADRENALINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.05-1 MCG/KG/MIN', 'BIC': '0.05-1 MCG/KG/MIN' },
            indicacion: 'CHOQUE SEPTICO'
        },
        'ADRENALINA': { 
            vias_permitidas: ['IV', 'BIC', 'IM', 'SC'],
            dosis: { 'IV': '0.1-2 MCG/KG/MIN', 'BIC': '0.1-2 MCG/KG/MIN', 'IM': '0.3-0.5 MG', 'SC': '0.3-0.5 MG' },
            indicacion: 'PCR/CHOQUE ANAFILACTICO'
        },
        'DOPAMINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '5-20 MCG/KG/MIN', 'BIC': '5-20 MCG/KG/MIN' },
            indicacion: 'CHOQUE CARDIOGENICO'
        },
        'DOBUTAMINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '2.5-20 MCG/KG/MIN', 'BIC': '2.5-20 MCG/KG/MIN' },
            indicacion: 'INSUFICIENCIA CARDIACA'
        },
        'VASOPRESINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.01-0.04 UI/MIN', 'BIC': '0.01-0.04 UI/MIN' },
            indicacion: 'CHOQUE DISTRIBUTIVO'
        },
        'TERLIPRESINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '1-2 MG/4H', 'BIC': '1-2 MG/4H' },
            indicacion: 'SANGRADO VARICEAL'
        },
        'MILRINONA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.125-0.75 MCG/KG/MIN', 'BIC': '0.125-0.75 MCG/KG/MIN' },
            indicacion: 'INSUFICIENCIA CARDIACA'
        },
        'LEVOSIMENDAN': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.05-0.2 MCG/KG/MIN', 'BIC': '0.05-0.2 MCG/KG/MIN' },
            indicacion: 'SHOCK CARDIOGENICO'
        },
        'NITROPRUSIATO': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.3-10 MCG/KG/MIN', 'BIC': '0.3-10 MCG/KG/MIN' },
            indicacion: 'EMERGENCIA HIPERTENSIVA'
        },
        'NITROGLICERINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '5-200 MCG/MIN', 'BIC': '5-200 MCG/MIN' },
            indicacion: 'ANGINA/EDEMA AGUDO'
        },
        'ESMOLOL': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '50-200 MCG/KG/MIN', 'BIC': '50-200 MCG/KG/MIN' },
            indicacion: 'TAQUICARDIA SVT'
        },
        'LABETALOL': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL'],
            dosis: { 'IV': '20-300 MG', 'BIC': '0.5-2 MG/MIN', 'ORAL': '100-400 MG/8-12H' },
            indicacion: 'EMERGENCIA HIPERTENSIVA'
        },
        'HIDRALAZINA': { 
            vias_permitidas: ['IV', 'IM', 'ORAL'],
            dosis: { 'IV': '10-40 MG', 'IM': '10-20 MG', 'ORAL': '25-100 MG/6-8H' },
            indicacion: 'EMERGENCIA HIPERTENSIVA'
        },
        'NICARDIPINO': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL'],
            dosis: { 'IV': '5-15 MG/H', 'BIC': '5-15 MG/H', 'ORAL': '20-40 MG/8H' },
            indicacion: 'EMERGENCIA HIPERTENSIVA'
        },
        'CLONIDINA': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL', 'TD'],
            dosis: { 'IV': '0.1-0.3 MG', 'BIC': '0.1-0.3 MG/8H', 'ORAL': '0.1-0.3 MG/8-12H', 'TD': '0.1-0.3 MG/SEMANA' },
            indicacion: 'SINDROME DE ABSTINENCIA'
        }
    },

    // MEDICAMENTOS NEFRÓLOGOS
    nefro: {
        'FUROSEMIDA': { 
            vias_permitidas: ['IV', 'BIC', 'IM', 'ORAL'],
            dosis: { 'IV': '20-200 MG', 'BIC': '0.5-1 MG/KG/D', 'IM': '20-40 MG', 'ORAL': '20-80 MG' },
            indicacion: 'DIURESIS FORZADA/EDEMA'
        },
        'BUMETANIDA': { 
            vias_permitidas: ['IV', 'IM', 'ORAL'],
            dosis: { 'IV': '1-4 MG', 'IM': '1-4 MG', 'ORAL': '1-4 MG' },
            indicacion: 'INSUFICIENCIA CARDIACA'
        },
        'TORASEMIDA': { 
            vias_permitidas: ['IV', 'ORAL'],
            dosis: { 'IV': '5-20 MG', 'ORAL': '5-20 MG' },
            indicacion: 'EDEMA/HIPERTENSION'
        },
        'METOLAZONA': { 
            vias_permitidas: ['ORAL'],
            dosis: { 'ORAL': '2.5-10 MG' },
            indicacion: 'DIURETICO DE ASA'
        },
        'ACETAZOLAMIDA': { 
            vias_permitidas: ['IV', 'ORAL'],
            dosis: { 'IV': '250-500 MG', 'ORAL': '250-500 MG' },
            indicacion: 'ALCALOSIS METABOLICA'
        },
        'HIDROCLOROTIAZIDA': { 
            vias_permitidas: ['ORAL'],
            dosis: { 'ORAL': '12.5-50 MG' },
            indicacion: 'HIPERTENSION/EDEMA'
        },
        'EPLERENONA': { 
            vias_permitidas: ['ORAL'],
            dosis: { 'ORAL': '25-50 MG' },
            indicacion: 'INSUFICIENCIA CARDIACA'
        },
        'ESPIRONOLACTONA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '25-100 MG', 'SNG': '25-100 MG' },
            indicacion: 'INSUFICIENCIA CARDIACA/ASCITIS'
        },
        'CLORTHALIDONA': { 
            vias_permitidas: ['ORAL'],
            dosis: { 'ORAL': '12.5-25 MG' },
            indicacion: 'HIPERTENSION'
        },
        'DOPAMINA BAJA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '1-3 MCG/KG/MIN', 'BIC': '1-3 MCG/KG/MIN' },
            indicacion: 'FLUJO RENAL'
        }
    },

    // MEDICAMENTOS GASTROINTESTINALES
    gastro: {
        'OMEPRAZOL': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL', 'SNG'],
            dosis: { 'IV': '20-40 MG/12H', 'BIC': '20-40 MG/12H', 'ORAL': '20-40 MG', 'SNG': '20-40 MG' },
            indicacion: 'PROTECCION GASTRICA/GERD'
        },
        'ESOMEPRAZOL': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL', 'SNG'],
            dosis: { 'IV': '20-40 MG/12H', 'BIC': '20-40 MG/12H', 'ORAL': '20-40 MG', 'SNG': '20-40 MG' },
            indicacion: 'SINDROME DE ZOLLINGER-ELLISON'
        },
        'PANTOPRAZOL': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL', 'SNG'],
            dosis: { 'IV': '40-80 MG/12H', 'BIC': '40-80 MG/12H', 'ORAL': '40-80 MG', 'SNG': '40-80 MG' },
            indicacion: 'PROTECCION GASTRICA'
        },
        'RANITIDINA': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '50-150 MG/6-8H', 'IM': '50 MG', 'ORAL': '150-300 MG', 'SNG': '150-300 MG' },
            indicacion: 'BLOQUEO H2'
        },
        'FAMOTIDINA': { 
            vias_permitidas: ['IV', 'ORAL', 'SNG'],
            dosis: { 'IV': '20-40 MG/12H', 'ORAL': '20-40 MG', 'SNG': '20-40 MG' },
            indicacion: 'PROTECCION GASTRICA'
        },
        'METOCLOPRAMIDA': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '10 MG', 'IM': '10 MG', 'ORAL': '10 MG/6-8H', 'SNG': '10 MG' },
            indicacion: 'NAUSEAS/VOMITOS'
        },
        'ONDANSETRON': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '4-8 MG', 'IM': '4-8 MG', 'ORAL': '4-8 MG', 'SNG': '4-8 MG' },
            indicacion: 'NAUSEAS POST-QUIMIOTERAPIA'
        },
        'DEXAMETASONA': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '4-8 MG', 'IM': '4-8 MG', 'ORAL': '4-8 MG', 'SNG': '4-8 MG' },
            indicacion: 'NAUSEAS REFRACTARIAS'
        },
        'HALOPERIDOL': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '0.5-2 MG', 'IM': '0.5-2 MG', 'ORAL': '0.5-2 MG', 'SNG': '0.5-2 MG' },
            indicacion: 'NAUSEAS REFRACTARIAS'
        },
        'LOPERAMIDA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '2-4 MG', 'SNG': '2-4 MG' },
            indicacion: 'DIARREA'
        },
        'OCTREOTIDA': { 
            vias_permitidas: ['IV', 'SC', 'IM'],
            dosis: { 'IV': '50-100 MCG', 'SC': '50-100 MCG/8H', 'IM': '20 MG/MES' },
            indicacion: 'SANGRADO DIGESTIVO'
        },
        'SUCRALFATO': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '1 G/6H', 'SNG': '1 G/6H' },
            indicacion: 'ULCERA GASTRICA'
        },
        'LACTULOSA': { 
            vias_permitidas: ['ORAL', 'SNG', 'RECTAL'],
            dosis: { 'ORAL': '15-30 ML', 'SNG': '15-30 ML', 'RECTAL': '300 ML' },
            indicacion: 'ENCEFALOPATIA HEPATICA'
        },
        'RIFAXIMINA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '400 MG/8H', 'SNG': '400 MG/8H' },
            indicacion: 'ENCEFALOPATIA HEPATICA'
        },
        'NEOMICINA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '500-1000 MG/6H', 'SNG': '500-1000 MG/6H' },
            indicacion: 'PREPARACION INTESTINAL'
        }
    },

    // MEDICACIÓN HEMATOLÓGICA
    hematologica: {
        'HEPARINA NO FRACCIONADA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '1000-2000 UI/H', 'BIC': '80 UI/KG/D' },
            indicacion: 'PROFILAXIS/TROMBOSIS'
        },
        'HEPARINA DE BAJO PESO MOLECULAR': { 
            vias_permitidas: ['SC', 'IV'],
            dosis: { 'SC': '40-60 MG', 'IV': '1 MG/KG' },
            indicacion: 'PROFILAXIS ANTICOAGULANTE'
        },
        'ENOXAPARINA': { 
            vias_permitidas: ['SC', 'IV'],
            dosis: { 'SC': '40-60 MG', 'IV': '1 MG/KG' },
            indicacion: 'PROFILAXIS ANTICOAGULANTE'
        },
        'DALTEPARINA': { 
            vias_permitidas: ['SC'],
            dosis: { 'SC': '2500-5000 UI' },
            indicacion: 'PROFILAXIS/TEP'
        },
        'TINZAPARINA': { 
            vias_permitidas: ['SC'],
            dosis: { 'SC': '3500-4500 UI' },
            indicacion: 'TROMBOSIS VENOSA PROFUNDA'
        },
        'WARFARINA': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '2-10 MG', 'SNG': '2-10 MG' },
            indicacion: 'ANTICOAGULACION CRONICA'
        },
        'RIVAROXABAN': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '10-20 MG', 'SNG': '10-20 MG' },
            indicacion: 'TROMBOEMBOLIA VENOSA'
        },
        'APIXABAN': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '2.5-5 MG', 'SNG': '2.5-5 MG' },
            indicacion: 'PREVENCION ACV'
        },
        'DABIGATRAN': { 
            vias_permitidas: ['ORAL', 'SNG'],
            dosis: { 'ORAL': '75-150 MG', 'SNG': '75-150 MG' },
            indicacion: 'TROMBOEMBOLIA'
        },
        'FONDAPARINUX': { 
            vias_permitidas: ['SC'],
            dosis: { 'SC': '2.5-10 MG' },
            indicacion: 'SINDROME CORONARIO AGUDO'
        },
        'ARGATROBAN': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '2 MCG/KG/MIN', 'BIC': '2 MCG/KG/MIN' },
            indicacion: 'TROMBOSIS CON HIT'
        },
        'BIVALIRUDINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '0.75-1.75 MG/KG/H', 'BIC': '0.75-1.75 MG/KG/H' },
            indicacion: 'INTERVENCION CORONARIA'
        },
        'DESMOPRESINA': { 
            vias_permitidas: ['IV', 'SC', 'INTRANASAL'],
            dosis: { 'IV': '0.3 MCG', 'SC': '0.3 MCG', 'INTRANASAL': '300 MCG' },
            indicacion: 'SANGRADO UREMICO'
        },
        'ACIDO TRANEXAMICO': { 
            vias_permitidas: ['IV', 'BIC', 'ORAL'],
            dosis: { 'IV': '1 G', 'BIC': '1 G/8H', 'ORAL': '1-1.5 G/6-8H' },
            indicacion: 'SANGRADO TRAUMATICO/QUIRURGICO'
        },
        'VITAMINA K': { 
            vias_permitidas: ['IV', 'IM', 'ORAL', 'SNG'],
            dosis: { 'IV': '1-10 MG', 'IM': '1-10 MG', 'ORAL': '1-10 MG', 'SNG': '1-10 MG' },
            indicacion: 'SANGRADO POR WARFARINA'
        },
        'PROTAMINA': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '1-1.5 MG', 'BIC': '1-1.5 MG' },
            indicacion: 'REVERSION HEPARINA'
        },
        'FILGRASTIM': { 
            vias_permitidas: ['SC', 'IV'],
            dosis: { 'SC': '300-600 MCG', 'IV': '300-600 MCG' },
            indicacion: 'NEUTROPENIA'
        },
        'EPOETINA ALFA': { 
            vias_permitidas: ['SC', 'IV'],
            dosis: { 'SC': '4000-10000 UI', 'IV': '4000-10000 UI' },
            indicacion: 'ANEMIA'
        },
        'FACTOR VIIA RECOMBINANTE': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '90 MCG/KG', 'BIC': '90 MCG/KG' },
            indicacion: 'SANGRADO MASIVO'
        },
        'COMPLEJO PROTROMBINICO': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '25-50 UI/KG', 'BIC': '25-50 UI/KG' },
            indicacion: 'SANGRADO ANTICOAGULANTE'
        },
        'FIBRINOGENO': { 
            vias_permitidas: ['IV', 'BIC'],
            dosis: { 'IV': '2-4 G', 'BIC': '2-4 G' },
            indicacion: 'HIPOFIBRINOGENEMIA'
        },
        'CRIOPRECIPITADOS': { 
            vias_permitidas: ['IV'],
            dosis: { 'IV': '6-10 UNIDADES' },
            indicacion: 'DEFICIENCIA FACTOR VIII'
        }
    }
};

/**
 * Obtiene dosis según medicamento y vía
 * @param {string} specialty - Especialidad (neurologicos, hemodinamicos, etc.)
 * @param {string} medicamento - Nombre del medicamento
 * @param {string} via - Vía de administración
 * @returns {string} - Dosis recomendada o vacío
 */
function getDosisPorVia(specialty, medicamento, via) {
    if (!MEDICATION_DICTIONARY_V2[specialty] || !MEDICATION_DICTIONARY_V2[specialty][medicamento]) {
        return '';
    }
    
    const med = MEDICATION_DICTIONARY_V2[specialty][medicamento];
    if (med.dosis && med.dosis[via]) {
        return med.dosis[via];
    }
    
    return '';
}

/**
 * Obtiene unidades permitidas para un medicamento según vía
 * @param {string} specialty - Especialidad
 * @param {string} medicamento - Nombre del medicamento
 * @param {string} via - Vía de administración
 * @returns {Array} - Lista de unidades permitidas
 */
function getUnidadesPorMedicamentoVia(specialty, medicamento, via) {
    const viaUpper = via ? via.toUpperCase() : 'IV';
    const viaData = MEDICATION_DICTIONARY_V2.vias[viaUpper];
    return viaData ? viaData.unidades : ['MG'];
}

/**
 * Genera HTML de opciones para select de unidades
 * @param {Array} unidades - Lista de unidades
 * @returns {string} - HTML de opciones
 */
function generarOpcionesUnidadesMedicamento(unidades) {
    if (!unidades || unidades.length === 0) {
        return '<option value="">SELECCIONAR...</option>';
    }
    return unidades.map(u => `<option value="${u}">${u}</option>`).join('');
}

/**
 * Normaliza nombre de medicamento (mayúsculas sin acentos)
 * @param {string} nombre - Nombre del medicamento
 * @returns {string} - Nombre normalizado
 */
function normalizeMedicationName(nombre) {
    if (!nombre || typeof nombre !== 'string') return '';
    
    const accents = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'
    };
    
    return nombre.split('').map(c => accents[c] || c).join('').toUpperCase().trim();
}

// Exportar funciones globales
window.MEDICATION_DICTIONARY_V2 = MEDICATION_DICTIONARY_V2;
window.getDosisPorVia = getDosisPorVia;
window.getUnidadesPorMedicamentoVia = getUnidadesPorMedicamentoVia;
window.generarOpcionesUnidadesMedicamento = generarOpcionesUnidadesMedicamento;
window.normalizeMedicationName = normalizeMedicationName;