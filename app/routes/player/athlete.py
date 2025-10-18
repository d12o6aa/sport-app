from flask import Blueprint, jsonify, request, render_template, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.health_record import HealthRecord
from app.models.athlete_profile import AthleteProfile
from app.extensions import db
from werkzeug.utils import secure_filename
import os
from . import athlete_bp

UPLOAD_FOLDER = "app/static/uploads/profile"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# MAIN PROFILE/DASHBOARD PAGE
# ============================================================
@athlete_bp.route("/profile")
@athlete_bp.route("/dashboard")  # يمكن الوصول من كلا الرابطين
@jwt_required()
def profile():
    """
    الصفحة الرئيسية (Dashboard) للرياضي
    تعرض: الصورة الشخصية، المعلومات الأساسية، الإحصائيات، النشاط الأخير
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != "athlete":
        return abort(403)
    
    # جلب البيانات
    profile = AthleteProfile.query.filter_by(user_id=user_id).first()
    hr = HealthRecord.query.filter_by(athlete_id=user_id)\
        .order_by(HealthRecord.recorded_at.desc()).first()
    
    return render_template(
        "athlete/profile.html", 
        user=user,
        profile=profile,
        hr=hr
    )


# ============================================================
# API: PROFILE IMAGE UPLOAD
# ============================================================
@athlete_bp.route("/api/profile/upload", methods=["POST"])
@jwt_required()
def upload_profile_image():
    """
    رفع صورة البروفايل
    يقبل: multipart/form-data مع حقل "image"
    يرجع: URL الصورة الجديدة
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    
    if not file or file.filename == "":
        return jsonify({"error": "Empty file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}), 400

    try:
        # حفظ الصورة
        filename = secure_filename(f"profile_{user_id}_{file.filename}")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # حذف الصورة القديمة (اختياري)
        if user.profile_image and user.profile_image != "default.jpg":
            old_path = os.path.join(UPLOAD_FOLDER, user.profile_image)
            if os.path.exists(old_path):
                os.remove(old_path)

        # تحديث قاعدة البيانات
        user.profile_image = filename
        db.session.commit()

        return jsonify({
            "msg": "Image uploaded successfully",
            "image_url": f"/static/uploads/{filename}"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================
# API: UPDATE PROFILE
# ============================================================
@athlete_bp.route("/profile/update", methods=["POST"])
@jwt_required()
def update_profile():
    """
    تحديث معلومات البروفايل
    يقبل: form-data أو JSON
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # تحديث الاسم
        full_name = request.form.get("full_name") or request.json.get("full_name")
        if full_name:
            user.name = full_name

        # جلب أو إنشاء ملف AthleteProfile
        profile = AthleteProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = AthleteProfile(user_id=user_id)
            db.session.add(profile)

        # تحديث البيانات الشخصية
        age = request.form.get("age") or request.json.get("age")
        gender = request.form.get("gender") or request.json.get("gender")
        weight = request.form.get("weight") or request.json.get("weight")
        height = request.form.get("height") or request.json.get("height")

        if age:
            profile.age = int(age)
        if gender:
            profile.gender = gender
        if weight:
            profile.weight = float(weight)
        if height:
            profile.height = float(height)

        # تحديث معدل نبضات القلب (Health Record)
        max_hr = request.form.get("max_hr") or request.json.get("max_hr")
        if max_hr:
            hr = HealthRecord.query.filter_by(athlete_id=user_id)\
                .order_by(HealthRecord.recorded_at.desc()).first()
            
            if not hr:
                hr = HealthRecord(athlete_id=user_id)
                db.session.add(hr)
            
            hr.heart_rate = int(max_hr)

        db.session.commit()

        return jsonify({
            "msg": "Profile updated successfully",
            "profile": {
                "name": user.name,
                "age": profile.age,
                "gender": profile.gender,
                "weight": profile.weight,
                "height": profile.height,
                "max_hr": hr.heart_rate if max_hr else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================
# API: GET PROFILE DATA (للـ API Calls)
# ============================================================
@athlete_bp.route("/api/profile", methods=["GET"])
@jwt_required()
def get_profile_data():
    """
    جلب بيانات البروفايل كاملة (JSON)
    للاستخدام في API calls أو Mobile apps
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = AthleteProfile.query.filter_by(user_id=user_id).first()
    hr = HealthRecord.query.filter_by(athlete_id=user_id)\
        .order_by(HealthRecord.recorded_at.desc()).first()

    # حساب BMI
    bmi = None
    if profile and profile.weight and profile.height:
        height_m = profile.height / 100
        bmi = round(profile.weight / (height_m * height_m), 1)

    return jsonify({
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "profile_image": f"/static/uploads/{user.profile_image}" if user.profile_image else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "profile": {
            "age": profile.age if profile else None,
            "gender": profile.gender if profile else None,
            "weight": profile.weight if profile else None,
            "height": profile.height if profile else None,
            "bmi": bmi
        },
        "health": {
            "heart_rate": hr.heart_rate if hr else None,
            "recorded_at": hr.recorded_at.isoformat() if hr else None
        }
    }), 200


# ============================================================
# API: DELETE PROFILE IMAGE
# ============================================================
@athlete_bp.route("/api/profile/delete_image", methods=["DELETE"])
@jwt_required()
def delete_profile_image():
    """
    حذف صورة البروفايل والعودة للصورة الافتراضية
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # حذف الملف من السيرفر
        if user.profile_image and user.profile_image != "default.jpg":
            old_path = os.path.join(UPLOAD_FOLDER, user.profile_image)
            if os.path.exists(old_path):
                os.remove(old_path)

        # تحديث قاعدة البيانات
        user.profile_image = "default.jpg"
        db.session.commit()

        return jsonify({
            "msg": "Profile image deleted",
            "image_url": "/static/uploads/default.jpg"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================
# OTHER ATHLETE ROUTES (unchanged)
# ============================================================

@athlete_bp.route('/unassigned_athletes', methods=['GET'])
@jwt_required()
def get_unassigned_athletes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can view unassigned athletes"}), 403

    athletes = User.query.filter_by(role='athlete', coach_id=None).all()
    result = [{"id": a.id, "email": a.email} for a in athletes]
    return jsonify(result)


@athlete_bp.route("/my_plans")
@jwt_required()
def my_plans():
    return render_template("athlete/my_plans.html")


@athlete_bp.route("/goals")
@jwt_required()
def goals():
    return render_template("athlete/goals.html")



@athlete_bp.route("/my_stats")
@jwt_required()
def my_stats():
    return render_template("athlete/progress.html")

