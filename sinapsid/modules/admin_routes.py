"""
SINAPSID DMA - Rutas de Administración
====================================
Dashboard de admin, gestión de usuarios, protocolos e instituciones.
Se importa en app.py para mantener modularidad.

IMPORTANTE: Este archivo debe importarse DESPUÉS de que `app` esté creado en app.py.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
from datetime import datetime

# Importar funciones del módulo admin
from modules.admin import (
    get_system_metrics, get_all_users, get_user_by_id_admin,
    create_user_admin, update_user_admin, reset_user_password,
    toggle_user_active, delete_user_admin,
    get_all_institutions, create_institution, update_institution,
    get_all_protocols, get_protocol_by_id, create_protocol,
    update_protocol, approve_protocol, close_protocol, delete_protocol,
    get_patient_enrollments, get_protocol_enrollments,
    get_patient_completeness, get_global_completeness,
    export_protocol_data, get_protocol_summary
)


# ============================================================
# DECORADOR: Requiere admin
# ============================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from modules.auth import get_current_user
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            if request.is_json or request.headers.get('Accept') == 'application/json':
                return jsonify({'error': 'Acceso denegado. Se requiere rol admin.'}), 403
            flash('Acceso denegado. Se requiere rol de administrador.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# FUNCIONES DE REGISTRO DE RUTAS
# ============================================================

def register_admin_routes(app):
    """Registra todas las rutas de administración en la app Flask."""
    
    # ============================================================
    # DASHBOARD PRINCIPAL
    # ============================================================
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        """Dashboard principal de administración."""
        from modules.auth import get_current_user
        
        current_user = get_current_user()
        metrics = get_system_metrics()
        users = get_all_users()
        protocols = get_all_protocols()
        institutions = get_all_institutions()
        
        # Completitud de expedientes
        try:
            completeness = get_global_completeness()
        except Exception:
            completeness = {}
        
        return render_template('admin.html',
            current_user=current_user,
            metrics=metrics,
            users=users,
            protocols=protocols,
            institutions=institutions,
            completeness=completeness
        )
    
    # ============================================================
    # USUARIOS API
    # ============================================================
    @app.route('/admin/api/users', methods=['POST'])
    @admin_required
    def admin_api_users_create():
        """Crea un nuevo usuario desde admin."""
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos JSON requeridos'}), 400
        
        required = ['username', 'email', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        try:
            user_id = create_user_admin(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                full_name=data.get('full_name'),
                institution_id=data.get('institution_id'),
                role=data.get('role', 'user')
            )
            return jsonify({'success': True, 'user_id': user_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/users/<int:user_id>/reset-password', methods=['POST'])
    @admin_required
    def admin_api_user_reset_password(user_id):
        """Resetea la contraseña de un usuario."""
        data = request.get_json()
        
        if not data or not data.get('new_password'):
            return jsonify({'success': False, 'error': 'Nueva contraseña requerida'}), 400
        
        try:
            success = reset_user_password(user_id, data['new_password'])
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/users/<int:user_id>/toggle', methods=['POST'])
    @admin_required
    def admin_api_user_toggle(user_id):
        """Activa/desactiva un usuario."""
        try:
            new_status = toggle_user_active(user_id)
            if new_status is not None:
                return jsonify({'success': True, 'is_active': new_status})
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/users/<int:user_id>', methods=['DELETE'])
    @admin_required
    def admin_api_user_delete(user_id):
        """Elimina un usuario."""
        try:
            success = delete_user_admin(user_id)
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    # ============================================================
    # INSTITUCIONES API
    # ============================================================
    @app.route('/admin/api/institutions', methods=['POST'])
    @admin_required
    def admin_api_institutions_create():
        """Crea una nueva institución."""
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos JSON requeridos'}), 400
        
        required = ['name', 'code']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        try:
            inst_id = create_institution(
                name=data['name'],
                code=data['code'],
                country=data.get('country', 'México'),
                state=data.get('state'),
                city=data.get('city'),
                type_=data.get('type', 'public'),
                contact_email=data.get('contact_email'),
                contact_phone=data.get('contact_phone'),
                contact_person=data.get('contact_person')
            )
            return jsonify({'success': True, 'institution_id': inst_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/institutions/<int:inst_id>', methods=['PUT'])
    @admin_required
    def admin_api_institution_update(inst_id):
        """Actualiza una institución."""
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos JSON requeridos'}), 400
        
        try:
            success = update_institution(inst_id, data)
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Institución no encontrada'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    # ============================================================
    # PROTOCOLOS API
    # ============================================================
    @app.route('/admin/api/protocols', methods=['POST'])
    @admin_required
    def admin_api_protocols_create():
        """Crea un nuevo protocolo."""
        data = request.get_json()
        from modules.auth import get_current_user
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos JSON requeridos'}), 400
        
        required = ['slug', 'name', 'form_definition']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        try:
            current_user = get_current_user()
            protocol_id = create_protocol(
                slug=data['slug'],
                name=data['name'],
                description=data.get('description'),
                objective=data.get('objective'),
                form_definition=data['form_definition'],
                visits=data.get('visits'),
                inclusion_criteria=data.get('inclusion_criteria'),
                exclusion_criteria=data.get('exclusion_criteria'),
                pi_name=data.get('pi_name'),
                pi_email=data.get('pi_email'),
                pi_institution=data.get('pi_institution'),
                created_by=current_user['id'] if current_user else None
            )
            return jsonify({'success': True, 'protocol_id': protocol_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/protocols/<int:protocol_id>/approve', methods=['POST'])
    @admin_required
    def admin_api_protocol_approve(protocol_id):
        """Aprueba un protocolo."""
        from modules.auth import get_current_user
        data = request.get_json() or {}
        
        try:
            current_user = get_current_user()
            success = approve_protocol(
                protocol_id=protocol_id,
                reviewed_by=current_user['id'] if current_user else None,
                review_notes=data.get('review_notes')
            )
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Protocolo no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/protocols/<int:protocol_id>/close', methods=['POST'])
    @admin_required
    def admin_api_protocol_close(protocol_id):
        """Cierra un protocolo."""
        try:
            success = close_protocol(protocol_id)
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Protocolo no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/admin/api/protocols/<int:protocol_id>', methods=['DELETE'])
    @admin_required
    def admin_api_protocol_delete(protocol_id):
        """Elimina un protocolo."""
        try:
            success = delete_protocol(protocol_id)
            if success:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Protocolo no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    # ============================================================
    # VISTA DETALLE DE PROTOCOLO
    # ============================================================
    @app.route('/admin/protocol/<int:protocol_id>')
    @admin_required
    def admin_protocol_detail(protocol_id):
        """Vista detalle de un protocolo con inscripciones."""
        from modules.auth import get_current_user
        
        protocol = get_protocol_by_id(protocol_id)
        if not protocol:
            flash('Protocolo no encontrado', 'error')
            return redirect(url_for('admin_dashboard'))
        
        enrollments = get_protocol_enrollments(protocol_id)
        summary = get_protocol_summary(protocol_id)
        
        return render_template('admin_protocol_detail.html',
            current_user=get_current_user(),
            protocol=protocol,
            enrollments=enrollments,
            summary=summary
        )
    
    
    # ============================================================
    # EXPORTACIÓN DE COHORTE
    # ============================================================
    @app.route('/admin/protocol/<int:protocol_id>/export')
    @admin_required
    def admin_protocol_export(protocol_id):
        """Exporta datos de cohorte en CSV."""
        import csv
        import io
        from flask import Response
        
        data = export_protocol_data(protocol_id)
        
        if not data:
            flash('No hay datos para exportar', 'warning')
            return redirect(url_for('admin_protocol_detail', protocol_id=protocol_id))
        
        # Crear CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        protocol = get_protocol_by_id(protocol_id)
        filename = f"cohorte-{protocol['slug']}-{datetime.now().strftime('%Y%m%d')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    
    
    # ============================================================
    # COMPLITUD API (para AJAX en dashboard)
    # ============================================================
    @app.route('/admin/api/completeness')
    @admin_required
    def admin_api_completeness():
        """Devuelve métricas de completitud en JSON."""
        try:
            completeness = get_global_completeness()
            return jsonify({'success': True, 'data': completeness})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    print("✅ Rutas de admin registradas correctamente")


# Para importar en app.py
from datetime import datetime
