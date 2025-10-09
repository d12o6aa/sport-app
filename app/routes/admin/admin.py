from flask import Blueprint, request, jsonify, render_template, url_for, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import generate_password_hash
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
from app import db
from app.models import (
    User, AdminProfile, CoachAthlete, ActivityLog, 
    AthleteProfile, WorkoutLog
)
from app.utils.decorators import inject_user_to_template 
from . import admin_bp

# =========================================================
# Helper Functions
# =========================================================

def is_superadmin(user):
    """Check if user is super admin"""
    return user and user.admin_profile and user.admin_profile.is_superadmin

def has_permission(user, permission_key):
    """Check if user has specific permission"""
    if is_superadmin(user):
        return True
    
    if user and user.admin_profile and user.admin_profile.permissions:
        return user.admin_profile.permissions.get(permission_key, False)
    
    return False

@admin_bp.context_processor
def inject_user_permissions():
    """Inject current user into all templates"""
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = User.query.get(user_id)
    except Exception:
        pass
    
    return {'current_user': user}

# =========================================================
# Admin Management Routes
# =========================================================

@admin_bp.route("/add_admin", methods=["POST"])
@jwt_required()
def add_admin():
    identity = get_jwt_identity()
    user = User.query.filter_by(id=identity).first()

    if not has_permission(user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not all([name, email, password]):
        return jsonify({"msg": "Missing data"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409

    password_hash = generate_password_hash(password)
    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        status='active',
        role='admin'
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Admin added successfully"}), 200

@admin_bp.route("/manage_admins")
@inject_user_to_template
def manage_admins(current_user): 
    if not current_user.is_admin:
        return "Unauthorized: You don't have permission to view this page.", 403

    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    pagination = (
        User.query
        .filter(User.role == "admin", User.id != current_user.id)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    admins = pagination.items
    admin_count = pagination.total
    active_count = User.query.filter_by(role='admin', status='active').count()
    suspended_count = User.query.filter_by(role='admin', status='suspended').count()
    
    return render_template("admin/manage_admins.html",
                            current_user=current_user,
                            admins=admins,
                            admin_count=admin_count,
                            active_count=active_count,
                            suspended_count=suspended_count,
                            pagination=pagination,
                            current_user_is_superadmin=is_superadmin(current_user))

@admin_bp.route("/edit_admin/<int:id>", methods=["GET", "POST"])
@jwt_required()
def edit_admin(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can edit other admins"}), 403

    admin = User.query.get_or_404(id)

    if request.method == "POST":
        data = request.get_json()
        admin.name = data.get("name", admin.name)
        admin.email = data.get("email", admin.email)
        db.session.commit()
        return jsonify({"msg": "Admin updated successfully"}), 200

    return jsonify({
        "id": admin.id,
        "name": admin.name,
        "email": admin.email
    }), 200

@admin_bp.route("/delete_admin/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_admin(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can delete admins"}), 403

    admin = User.query.get_or_404(id)
    db.session.delete(admin)
    db.session.commit()
    return jsonify({"msg": "Admin deleted successfully"}), 200

@admin_bp.route("/toggle_active/<int:id>", methods=["PATCH"])
@jwt_required()
def toggle_active(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    admin = User.query.get_or_404(id)
    if admin.status == 'active':
        admin.status = 'suspended'
    else:
        admin.status = 'active'
    db.session.commit()

    return jsonify({
        "msg": f"Admin {'activated' if admin.status == 'active' else 'deactivated'} successfully",
        "status": admin.status
    }), 200

@admin_bp.route("/update_admin/<int:id>", methods=["PUT"])
@jwt_required()
def update_admin(id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can update admins"}), 403

    data = request.get_json()
    user = User.query.get_or_404(id)
    return update_user_logic(user, data)

@admin_bp.route("/get_admin/<int:id>", methods=["GET"])
@jwt_required()
def get_admin(id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Unauthorized"}), 403

    admin = User.query.filter_by(id=id, role="admin").first()
    if not admin:
        return jsonify({"msg": "Admin not found"}), 404
        
    admin_profile = AdminProfile.query.filter_by(user_id=id).first()
    
    permissions = admin_profile.permissions if admin_profile else {}
    is_super = admin_profile.is_superadmin if admin_profile else False

    return jsonify({
        "name": admin.name,
        "email": admin.email,
        "is_superadmin": is_super,
        "permissions": permissions,
        "role": admin.role
    })

@admin_bp.route("/bulk_delete", methods=["POST"])
@jwt_required()
def bulk_delete():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403
    
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"msg": "No user IDs provided"}), 400
    ids = [uid for uid in ids if uid != current_user.id]
    User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"msg": "Users deleted successfully"}), 200

@admin_bp.route("/bulk_change_role", methods=["POST"])
@jwt_required()
def bulk_change_role():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    data = request.get_json()
    ids = data.get("ids", [])
    new_role = data.get("role")
    if not ids or not new_role:
        return jsonify({"msg": "IDs and new role are required"}), 400
    ids = [uid for uid in ids if uid != current_user.id]
    User.query.filter(User.id.in_(ids)).update({"role": new_role}, synchronize_session=False)
    db.session.commit()
    return jsonify({"msg": f"Users updated to {new_role} successfully"}), 200

@admin_bp.route("/reset_password/<int:user_id>", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    new_password = "Default@123"
    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": f"Password reset to {new_password}"}), 200

# =========================================================
# ✅ NEW: Unassigned Athletes Management
# =========================================================

@admin_bp.route("/unassigned-athletes", methods=["GET"])
@jwt_required()
def get_unassigned_athletes():
    """Get all unassigned athletes"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Get athletes with no active coach link
        unassigned_athletes = db.session.query(
            User,
            CoachAthlete
        ).outerjoin(
            CoachAthlete,
            and_(
                CoachAthlete.athlete_id == User.id,
                CoachAthlete.is_active == True,
                CoachAthlete.status == 'approved'
            )
        ).filter(
            User.role == 'athlete',
            User.is_deleted == False,
            CoachAthlete.id == None
        ).all()
        
        # Get athletes with unassigned status
        unassigned_by_coach = db.session.query(
            User,
            CoachAthlete
        ).join(
            CoachAthlete, CoachAthlete.athlete_id == User.id
        ).filter(
            User.role == 'athlete',
            User.is_deleted == False,
            CoachAthlete.status == 'unassigned',
            CoachAthlete.is_active == False
        ).all()
        
        athlete_list = []
        
        # Process completely unassigned athletes
        for record in unassigned_athletes:
            user = record[0]
            athlete_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else None,
                "unassigned_reason": "Never assigned",
                "previous_coach": None,
                "unassigned_at": None
            })
        
        # Process athletes unassigned by coaches
        for record in unassigned_by_coach:
            user = record[0]
            coach_link = record[1]
            
            previous_coach = User.query.get(coach_link.coach_id)
            
            athlete_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else None,
                "unassigned_reason": "Removed by coach",
                "previous_coach": {
                    "id": previous_coach.id,
                    "name": previous_coach.name
                } if previous_coach else None,
                "unassigned_at": coach_link.assigned_at.strftime("%Y-%m-%d") if coach_link.assigned_at else None
            })
        
        return jsonify(athlete_list), 200
        
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@admin_bp.route("/assign-athlete", methods=["POST"])
@jwt_required()
def assign_athlete_to_coach():
    """Assign athlete to coach"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    athlete_id = data.get("athlete_id")
    coach_id = data.get("coach_id")
    
    if not athlete_id or not coach_id:
        return jsonify({"msg": "Missing athlete_id or coach_id"}), 400
    
    try:
        # Verify athlete exists
        athlete = User.query.filter_by(id=athlete_id, role='athlete').first()
        if not athlete:
            return jsonify({"msg": "Athlete not found"}), 404
        
        # Verify coach exists
        coach = User.query.filter_by(id=coach_id, role='coach').first()
        if not coach:
            return jsonify({"msg": "Coach not found"}), 404
        
        # Check existing link
        existing_link = CoachAthlete.query.filter_by(
            coach_id=coach_id,
            athlete_id=athlete_id
        ).first()
        
        if existing_link:
            # Reactivate existing link
            existing_link.is_active = True
            existing_link.status = 'approved'
            existing_link.assigned_at = datetime.utcnow()
            message = "Athlete reassigned to coach successfully"
        else:
            # Create new link
            new_link = CoachAthlete(
                coach_id=coach_id,
                athlete_id=athlete_id,
                assigned_at=datetime.utcnow(),
                status='approved',
                is_active=True,
                approved_by=identity
            )
            db.session.add(new_link)
            message = "Athlete assigned to coach successfully"
        
        # Deactivate other active links
        other_links = CoachAthlete.query.filter(
            CoachAthlete.athlete_id == athlete_id,
            CoachAthlete.coach_id != coach_id,
            CoachAthlete.is_active == True
        ).all()
        
        for link in other_links:
            link.is_active = False
            link.status = 'unassigned'
        
        # Log activity
        activity = ActivityLog(
            user_id=identity,
            action="Assigned athlete to coach",
            details={
                "athlete_id": athlete_id,
                "athlete_name": athlete.name,
                "coach_id": coach_id,
                "coach_name": coach.name,
                "admin_action": True
            },
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            "msg": message,
            "athlete_id": athlete_id,
            "coach_id": coach_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error assigning athlete: {str(e)}"}), 500

@admin_bp.route("/bulk-assign", methods=["POST"])
@jwt_required()
def bulk_assign_athletes():
    """Bulk assign athletes to a coach"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    athlete_ids = data.get("athlete_ids", [])
    coach_id = data.get("coach_id")
    
    if not athlete_ids or not coach_id:
        return jsonify({"msg": "Missing athlete_ids or coach_id"}), 400
    
    try:
        # Verify coach
        coach = User.query.filter_by(id=coach_id, role='coach').first()
        if not coach:
            return jsonify({"msg": "Coach not found"}), 404
        
        success_count = 0
        failed_athletes = []
        
        for athlete_id in athlete_ids:
            athlete = User.query.filter_by(id=athlete_id, role='athlete').first()
            if not athlete:
                failed_athletes.append({"id": athlete_id, "reason": "Athlete not found"})
                continue
            
            # Check existing link
            existing_link = CoachAthlete.query.filter_by(
                coach_id=coach_id,
                athlete_id=athlete_id
            ).first()
            
            if existing_link:
                existing_link.is_active = True
                existing_link.status = 'approved'
                existing_link.assigned_at = datetime.utcnow()
            else:
                new_link = CoachAthlete(
                    coach_id=coach_id,
                    athlete_id=athlete_id,
                    assigned_at=datetime.utcnow(),
                    status='approved',
                    is_active=True,
                    approved_by=identity
                )
                db.session.add(new_link)
            
            # Deactivate other links
            other_links = CoachAthlete.query.filter(
                CoachAthlete.athlete_id == athlete_id,
                CoachAthlete.coach_id != coach_id,
                CoachAthlete.is_active == True
            ).all()
            
            for link in other_links:
                link.is_active = False
                link.status = 'unassigned'
            
            success_count += 1
        
        # Log activity
        activity = ActivityLog(
            user_id=identity,
            action="Bulk assigned athletes to coach",
            details={
                "coach_id": coach_id,
                "coach_name": coach.name,
                "success_count": success_count,
                "failed_count": len(failed_athletes),
                "admin_action": True
            },
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({
            "msg": f"Bulk assignment completed. {success_count} athletes assigned.",
            "success_count": success_count,
            "failed_athletes": failed_athletes
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error in bulk assignment: {str(e)}"}), 500

@admin_bp.route("/coaches-list", methods=["GET"])
@jwt_required()
def get_coaches_list():
    """Get all coaches for assignment dropdown"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        coaches = User.query.filter_by(
            role='coach',
            is_deleted=False,
            status='active'
        ).all()
        
        coach_list = []
        for coach in coaches:
            assigned_count = CoachAthlete.query.filter_by(
                coach_id=coach.id,
                is_active=True,
                status='approved'
            ).count()
            
            coach_list.append({
                "id": coach.id,
                "name": coach.name,
                "email": coach.email,
                "assigned_athletes": assigned_count,
                "status": coach.status
            })
        
        return jsonify(coach_list), 200
        
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@admin_bp.route("/athlete/<int:athlete_id>/assignment-history", methods=["GET"])
@jwt_required()
def get_assignment_history(athlete_id):
    """Get assignment history for an athlete"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        history = db.session.query(
            CoachAthlete,
            User
        ).join(
            User, User.id == CoachAthlete.coach_id
        ).filter(
            CoachAthlete.athlete_id == athlete_id
        ).order_by(desc(CoachAthlete.assigned_at)).all()
        
        history_list = []
        for record in history:
            link = record[0]
            coach = record[1]
            
            history_list.append({
                "coach_id": coach.id,
                "coach_name": coach.name,
                "assigned_at": link.assigned_at.strftime("%Y-%m-%d %H:%M") if link.assigned_at else None,
                "status": link.status,
                "is_active": link.is_active
            })
        
        return jsonify(history_list), 200
        
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@admin_bp.route("/athlete/<int:athlete_id>/delete-permanent", methods=["DELETE"])
@jwt_required()
def delete_athlete_permanently(athlete_id):
    """Permanently delete an athlete (soft delete)"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can permanently delete athletes"}), 403

    try:
        athlete = User.query.filter_by(id=athlete_id, role='athlete').first()
        if not athlete:
            return jsonify({"msg": "Athlete not found"}), 404
        
        # Soft delete
        athlete.is_deleted = True
        athlete.delete_requested_at = datetime.utcnow()
        
        # Deactivate all links
        CoachAthlete.query.filter_by(athlete_id=athlete_id).update({
            'is_active': False,
            'status': 'unassigned'
        })
        
        # Log activity
        activity = ActivityLog(
            user_id=identity,
            action="Deleted athlete permanently",
            details={
                "athlete_id": athlete_id,
                "athlete_name": athlete.name,
                "admin_action": True
            },
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({"msg": "Athlete deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error deleting athlete: {str(e)}"}), 500

@admin_bp.route("/athlete/<int:athlete_id>/restore", methods=["POST"])
@jwt_required()
def restore_athlete(athlete_id):
    """Restore a deleted athlete"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can restore athletes"}), 403

    try:
        athlete = User.query.get(athlete_id)
        if not athlete:
            return jsonify({"msg": "Athlete not found"}), 404
        
        athlete.is_deleted = False
        athlete.delete_requested_at = None
        athlete.status = 'active'
        
        # Log activity
        activity = ActivityLog(
            user_id=identity,
            action="Restored athlete",
            details={
                "athlete_id": athlete_id,
                "athlete_name": athlete.name,
                "admin_action": True
            },
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        
        db.session.commit()
        
        return jsonify({"msg": "Athlete restored successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error restoring athlete: {str(e)}"}), 500

@admin_bp.route("/assignment-stats", methods=["GET"])
@jwt_required()
def get_assignment_stats():
    """Get assignment statistics for dashboard"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Total athletes
        total_athletes = User.query.filter_by(
            role='athlete',
            is_deleted=False
        ).count()
        
        # Assigned athletes
        assigned_athletes = db.session.query(
            func.count(func.distinct(CoachAthlete.athlete_id))
        ).filter(
            CoachAthlete.is_active == True,
            CoachAthlete.status == 'approved'
        ).scalar()
        
        # Unassigned athletes
        unassigned_athletes = total_athletes - (assigned_athletes or 0)
        
        # Total coaches
        total_coaches = User.query.filter_by(
            role='coach',
            is_deleted=False,
            status='active'
        ).count()
        
        # Recent assignments (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_assignments = CoachAthlete.query.filter(
            CoachAthlete.assigned_at >= seven_days_ago,
            CoachAthlete.is_active == True
        ).count()
        
        return jsonify({
            "total_athletes": total_athletes,
            "assigned_athletes": assigned_athletes or 0,
            "unassigned_athletes": unassigned_athletes,
            "total_coaches": total_coaches,
            "recent_assignments": recent_assignments
        }), 200
        
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@admin_bp.route("/manage-unassigned-athletes")
@jwt_required()
def manage_unassigned_athletes_page():
    """Render unassigned athletes management page"""
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user.is_admin:
        return "Unauthorized", 403
    
    return render_template("admin/manage_unassigned_athletes.html", current_user=current_user)


# =========================================================
# Existing Routes (kept as is)
# =========================================================


@admin_bp.route("/add_user", methods=["GET"])
def add_user_page():
    return render_template("add_user.html")

@admin_bp.route("/add_user", methods=["POST"])
@jwt_required()
def add_user():
    print("Request headers:", request.headers)
    if request.method == "POST":
        identity = get_jwt_identity()
        print("JWT identity:", identity, "Type:", type(identity))
        user = User.query.filter_by(id=identity).first()

        if not user or user.role.lower() != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        if not all([name, email, password, role]):
            return jsonify({"msg": "Missing data"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "Email already exists"}), 409

        password_hash = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"msg": "User added successfully", "redirect_url": url_for('main_bp.home')}), 200
    return jsonify({"msg": "Use POST to add user"}), 405



@admin_bp.route('/user_management')
@jwt_required()
def user_management():
    total_users = User.query.count()
    admins = User.query.filter_by(role='admin').count()
    coaches = User.query.filter_by(role='coach').count()
    athletes = User.query.filter_by(role='athlete').count()
    unassigned = User.query.filter_by(status='suspended').count()

    return render_template(
        'admin/user_management.html',
        total_users=total_users,
        admins=admins,
        coaches=coaches,
        athletes=athletes,
        unassigned=unassigned
    )


def update_user_logic(user, data):
    """لوجيك موحّد لتحديث أي يوزر"""
    new_role = data.get("role")

    if new_role and new_role != user.role:
        # Reset old relations
        if user.role == "coach":
            for link in user.athlete_links.all():
                db.session.delete(link)

        if user.role == "athlete":
            for group in user.group_assignments.all():
                db.session.delete(group)
            for plan in user.plan_assignments.all():
                db.session.delete(plan)

        # ✅ Update role (admin / coach / athlete)
        if new_role in ["admin", "coach", "athlete"]:
            user.role = new_role

    # ✅ Handle super_admin flag
    if "is_superadmin" in data and user.role == "admin":
        if not user.admin_profile:
            user.admin_profile = AdminProfile(user_id=user.id)
        user.admin_profile.is_superadmin = bool(data["is_superadmin"])

    # ✅ Update permissions
    if "permissions" in data:
        if not user.admin_profile:
            user.admin_profile = AdminProfile(user_id=user.id)
        user.admin_profile.permissions = data["permissions"]

    db.session.commit()
    return jsonify({"msg": "User updated successfully"}), 200


@admin_bp.route("/some-protected-route")
@jwt_required()
def protected_area():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    # check permission properly
    if not user.admin_profile or not user.admin_profile.permissions.get("can_manage_users", False):
        return "Unauthorized", 403

    return jsonify({"msg": "Welcome, authorized user!"}), 200


@admin_bp.route("/change_role/<int:user_id>", methods=["POST"])
@jwt_required()
def change_role(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin" or not current_user.admin_profile or not current_user.admin_profile.is_superadmin:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    new_role = data.get("role")

    if new_role not in ["admin", "coach", "athlete"]:
        return jsonify({"msg": "Invalid role"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    old_role = user.role
    user.role = new_role
    db.session.commit()

    return jsonify({"msg": f"Role changed from {old_role} to {new_role} successfully"}), 200

@admin_bp.route("/profile")
@jwt_required()
def user_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("users-profile.html", user=user)

@admin_bp.route("/image")
@jwt_required()
def image_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("shared/base.html", user=user)

@admin_bp.route("/profile", methods=["POST"])
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    user.name = data.get("name")
    db.session.commit()
    return redirect(url_for("admin.user_profile"))

@admin_bp.route("/update-password", methods=["POST"])
@jwt_required()
def update_password():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not user.check_password(current_password):
        return jsonify({"msg": "Wrong current password"}), 400

    if new_password != confirm_password:
        return jsonify({"msg": "Passwords do not match"}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": "Password updated successfully"}), 200

