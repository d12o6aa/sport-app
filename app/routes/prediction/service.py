# app/routes/prediction/service.py
import pickle
import pandas as pd

# ---------------- Load Models ----------------
with open('app/routes/prediction/models/model1.pkl', 'rb') as f:
    model1 = pickle.load(f)

with open('app/routes/prediction/models/model2.pkl', 'rb') as f:
    model2 = pickle.load(f)

with open('app/routes/prediction/models/best_xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

# ---------------- Load Features ----------------
with open('app/routes/prediction/features/model1_features.pkl', 'rb') as f:
    model1_features = pickle.load(f)

with open('app/routes/prediction/features/model2_features.pkl', 'rb') as f:
    model2_features = pickle.load(f)

with open('app/routes/prediction/features/xgboost_features.pkl', 'rb') as f:
    xgb_features = pickle.load(f)

# ---------------- Helpers ----------------
def encode_injury_severity(severity):
    mapping = {'Mild': 0, 'Moderate': 1, 'Severe': 2}
    return mapping.get(severity, 1)

def recommend_periodization(pred_class):
    if pred_class == 0:
        return "Taper: reduce intensity and volume."
    elif pred_class == 1:
        return "Build: maintain or moderately increase load."
    elif pred_class == 2:
        return "Peak: maximize performance with high intensity."
    return "Monitor and reassess."

# ---------------- Prediction ----------------
def predict_all(input_data: dict):
    df = pd.DataFrame([input_data])

    # ✅ تأكيد إن الأعمدة الرقمية كلها رقمية
    numeric_cols = [
        "heart_rate", "sleep_hours", "dietary_intake",
        "training_days_per_week", "recovery_days_per_week",
        "Heart_Rate_(HR)", "Muscle_Tension_(MT)",
        "Body_Temperature_(BT)", "Breathing_Rate_(BR)",
        "Blood_Pressure_Systolic_(BP)", "Blood_Pressure_Diastolic_(BP)",
        "Training_Duration_(TD)", "Wavelet_Features_(WF)", "Feature_Weights_(FW)"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ✅ One-hot encode
    categorical_cols = ["Training_Intensity_(TI)", "Training_Type_(TT)", "Time_Interval_(TI)", "Phase_of_Training_(PT)"]
    df = pd.get_dummies(df, columns=categorical_cols)

    # ---------------- Model 1 (Injury Severity) ----------------
    for col in model1_features:
        if col not in df.columns:
            df[col] = 0
    X1 = df[model1_features]
    injury_pred = model1.predict(X1)[0]
    injury_encoded = encode_injury_severity(injury_pred)

    df['injury_severity_pred'] = injury_pred
    df['injury_severity_encoded'] = injury_encoded

    # ---------------- Model 2 (Recovery) ----------------
    for col in model2_features:
        if col not in df.columns:
            df[col] = 0
    X2 = df[model2_features]
    recovery_pred = model2.predict(X2)[0]

    # ---------------- Model 3 (Performance / XGB) ----------------
    for col in xgb_features:
        if col not in df.columns:
            df[col] = 0
    X3 = df[xgb_features]
    performance_class = xgb_model.predict(X3)[0]
    periodization_recommendation = recommend_periodization(int(performance_class))

    # ✅ ممكن نرجّع readiness score بسيط (0–100)
    readiness_score = int((100 - (injury_encoded * 30)) + (recovery_pred * 10))
    readiness_score = max(0, min(readiness_score, 100))  # bound 0–100

    return {
        "injury_severity_prediction": str(injury_pred),
        "recovery_success_prediction": int(recovery_pred),
        "performance_class": int(performance_class),
        "periodization_recommendation": periodization_recommendation,
        "readiness_score": readiness_score
    }
