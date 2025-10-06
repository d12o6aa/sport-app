from flask import Blueprint, jsonify, render_template, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_, or_, desc, asc, cast, Float
from datetime import datetime, timedelta, date
import json
import io
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import xlsxwriter

from app import db
from app.models import (
    User, CoachAthlete, TrainingPlan, WorkoutLog, 
    AthleteProgress, Equipment
)
from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/reports", methods=["GET"])
@jwt_required()
def reports():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Get date range (default to last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Calculate statistics
    stats = calculate_dashboard_stats(start_date, end_date)
    
    # Get coach performance data
    coaches_performance = get_coaches_performance(start_date, end_date)
    
    return render_template(
        "admin/reports.html",
        num_members=stats['total_members'],
        avg_progress=stats['avg_progress'],
        coaches_performance=coaches_performance,
        stats=stats
    )

# ================================
# Statistics Calculation Functions
# ================================

def calculate_dashboard_stats(start_date, end_date):
    """Calculate comprehensive dashboard statistics"""
    
    # Total members
    total_members = User.query.filter_by(is_deleted=False).count()
    new_members = User.query.filter(
        User.created_at >= datetime.combine(start_date, datetime.min.time()),
        User.is_deleted == False
    ).count()
    
    # Average progress
    avg_progress_result = db.session.query(func.avg(cast(AthleteProgress.progress, Float))).filter(
        AthleteProgress.date >= start_date,
        AthleteProgress.date <= end_date
    ).scalar()
    avg_progress = float(avg_progress_result) if avg_progress_result else 0.0
    
    # Workout statistics
    total_workouts = WorkoutLog.query.filter(
        WorkoutLog.date >= start_date,
        WorkoutLog.date <= end_date
    ).count()
    
    completed_workouts = WorkoutLog.query.filter(
        WorkoutLog.date >= start_date,
        WorkoutLog.date <= end_date,
        WorkoutLog.completion_status == 'completed'
    ).count()
    
    # Active training plans
    active_plans = TrainingPlan.query.filter_by(status='active').count()
    
    # Equipment usage
    equipment_stats = {
        'total': Equipment.query.count(),
        'available': Equipment.query.filter_by(status='available').count(),
        'maintenance': Equipment.query.filter_by(status='maintenance').count()
    }
    
    # Member activity stats
    active_members = User.query.join(WorkoutLog).filter(
        WorkoutLog.date >= start_date,
        WorkoutLog.date <= end_date,
        User.role == 'athlete'
    ).distinct().count()
    
    return {
        'total_members': total_members,
        'new_members': new_members,
        'avg_progress': avg_progress,
        'total_workouts': total_workouts,
        'completed_workouts': completed_workouts,
        'active_plans': active_plans,
        'equipment_stats': equipment_stats,
        'active_members': active_members,
        'member_change': (new_members / max(total_members - new_members, 1)) * 100
    }

def get_coaches_performance(start_date, end_date):
    """Get coach performance rankings"""
    
    coaches_performance = db.session.query(
        User.id.label("coach_id"),
        User.name.label("coach_name"),
        func.count(CoachAthlete.athlete_id).label("total_athletes"),
        func.avg(cast(AthleteProgress.progress, Float)).label("avg_progress")
    ).join(
        CoachAthlete, CoachAthlete.coach_id == User.id
    ).join(
        AthleteProgress, AthleteProgress.athlete_id == CoachAthlete.athlete_id
    ).filter(
        User.role == "coach",
        AthleteProgress.date >= start_date,
        AthleteProgress.date <= end_date
    ).group_by(
        User.id, User.name
    ).order_by(
        desc("avg_progress")
    ).all()
    
    return coaches_performance

# ================================
# API Endpoints for Dynamic Data
# ================================

@admin_bp.route("/api/reports/stats", methods=["GET"])
@jwt_required()
def get_reports_stats():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    stats = calculate_dashboard_stats(start_date, end_date)
    
    return jsonify({
        "success": True,
        "stats": stats,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    })

@admin_bp.route("/api/reports/member-activity", methods=["GET"])
@jwt_required()
def get_member_activity():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    members = db.session.query(
        User.id,
        User.name,
        User.email,
        func.count(WorkoutLog.id).label('total_workouts'),
        func.avg(cast(AthleteProgress.progress, Float)).label('avg_progress'),
        func.max(WorkoutLog.logged_at).label('last_active')
    ).outerjoin(
        WorkoutLog, WorkoutLog.athlete_id == User.id
    ).outerjoin(
        AthleteProgress, AthleteProgress.athlete_id == User.id
    ).filter(
        User.role == 'athlete',
        User.is_deleted == False
    ).group_by(
        User.id, User.name, User.email
    ).all()
    
    member_data = []
    for member in members:
        last_active = member.last_active
        if last_active:
            time_diff = datetime.now() - last_active
            if time_diff.days == 0:
                last_active_str = f"{time_diff.seconds // 3600} hours ago"
            else:
                last_active_str = f"{time_diff.days} days ago"
        else:
            last_active_str = "Never"
        
        status = 'active' if member.last_active and (datetime.now() - member.last_active).days < 7 else 'inactive'
        
        member_data.append({
            'id': member.id,
            'name': member.name,
            'email': member.email,
            'workouts': member.total_workouts or 0,
            'progress': round(member.avg_progress or 0, 1),
            'last_active': last_active_str,
            'status': status
        })
    
    return jsonify({
        "success": True,
        "members": member_data
    })

# ================================
# Export Functions
# ================================

@admin_bp.route("/api/reports/export", methods=["POST"])
@jwt_required()
def export_report():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    data = request.get_json()
    export_format = data.get('format', 'pdf')
    report_type = data.get('report_type', 'overview')
    date_range = data.get('date_range', 30)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=int(date_range))
    stats = calculate_dashboard_stats(start_date, end_date)
    coaches_performance = get_coaches_performance(start_date, end_date)
    
    try:
        if export_format == 'pdf':
            return export_pdf_report(stats, coaches_performance, start_date, end_date)
        elif export_format == 'excel':
            return export_excel_report(stats, coaches_performance, start_date, end_date)
        elif export_format == 'csv':
            return export_csv_report(stats, coaches_performance, start_date, end_date)
        else:
            return jsonify({"success": False, "error": "Invalid format"}), 400
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def export_pdf_report(stats, coaches_performance, start_date, end_date):
    """Generate PDF report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title = Paragraph(f"<b>Gym Management Report</b><br/>{start_date} to {end_date}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Members', str(stats['total_members'])],
        ['New Members', str(stats['new_members'])],
        ['Average Progress', f"{stats['avg_progress']:.1f}%"],
        ['Active Plans', str(stats['active_plans'])],
        ['Completed Workouts', str(stats['completed_workouts'])]
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    elements.append(Paragraph("<b>Coach Performance Rankings</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    coach_data = [['Rank', 'Coach Name', 'Athletes', 'Avg Progress']]
    for idx, coach in enumerate(coaches_performance, 1):
        coach_data.append([
            str(idx),
            coach.coach_name,
            str(coach.total_athletes),
            f"{coach.avg_progress:.1f}%"
        ])
    
    coach_table = Table(coach_data, colWidths=[50, 150, 100, 100])
    coach_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(coach_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'gym_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )

def export_excel_report(stats, coaches_performance, start_date, end_date):
    """Generate Excel report"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Summary')
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4154f1',
        'font_color': 'white',
        'align': 'center'
    })
    
    worksheet.write('A1', 'Gym Management Report', header_format)
    worksheet.write('A2', f'Period: {start_date} to {end_date}')
    
    row = 4
    worksheet.write(row, 0, 'Metric', header_format)
    worksheet.write(row, 1, 'Value', header_format)
    
    row += 1
    worksheet.write(row, 0, 'Total Members')
    worksheet.write(row, 1, stats['total_members'])
    
    row += 1
    worksheet.write(row, 0, 'New Members')
    worksheet.write(row, 1, stats['new_members'])
    
    row += 1
    worksheet.write(row, 0, 'Average Progress')
    worksheet.write(row, 1, f"{stats['avg_progress']:.1f}%")
    
    row += 1
    worksheet.write(row, 0, 'Active Plans')
    worksheet.write(row, 1, stats['active_plans'])

    row += 1
    worksheet.write(row, 0, 'Completed Workouts')
    worksheet.write(row, 1, stats['completed_workouts'])
    
    coach_sheet = workbook.add_worksheet('Coach Performance')
    coach_sheet.write(0, 0, 'Rank', header_format)
    coach_sheet.write(0, 1, 'Coach Name', header_format)
    coach_sheet.write(0, 2, 'Total Athletes', header_format)
    coach_sheet.write(0, 3, 'Avg Progress', header_format)
    
    for idx, coach in enumerate(coaches_performance, 1):
        coach_sheet.write(idx, 0, idx)
        coach_sheet.write(idx, 1, coach.coach_name)
        coach_sheet.write(idx, 2, coach.total_athletes)
        coach_sheet.write(idx, 3, f"{coach.avg_progress:.1f}%")
    
    workbook.close()
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'gym_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

def export_csv_report(stats, coaches_performance, start_date, end_date):
    """Generate CSV report"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Gym Management Report'])
    writer.writerow([f'Period: {start_date} to {end_date}'])
    writer.writerow([])
    
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Members', stats['total_members']])
    writer.writerow(['New Members', stats['new_members']])
    writer.writerow(['Average Progress', f"{stats['avg_progress']:.1f}%"])
    writer.writerow(['Active Plans', stats['active_plans']])
    writer.writerow(['Completed Workouts', stats['completed_workouts']])
    writer.writerow([])
    
    writer.writerow(['Coach Performance'])
    writer.writerow(['Rank', 'Coach Name', 'Total Athletes', 'Avg Progress'])
    for idx, coach in enumerate(coaches_performance, 1):
        writer.writerow([
            idx,
            coach.coach_name,
            coach.total_athletes,
            f"{coach.avg_progress:.1f}%"
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'gym_report_{datetime.now().strftime("%Y%m%d")}.csv'
    )