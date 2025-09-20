from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Subscription, User
from datetime import datetime

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/subscription_management", methods=["GET"])
@jwt_required()
def subscription_management():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    subscriptions = Subscription.query.all()
    return render_template("admin/subscription_management.html", subscriptions=subscriptions)

@admin_bp.route("/add_subscription", methods=["POST"])
@jwt_required()
def add_subscription():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.form
    subscription = Subscription(
        user_id=data.get("user_id"),
        plan_type=data.get("plan_type"),
        amount=data.get("amount"),
        start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d"),
        end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d"),
        status=data.get("status", "active")
    )
    db.session.add(subscription)
    db.session.commit()
    flash("Subscription added successfully!", "success")
    return redirect(url_for("admin.subscription_management"))