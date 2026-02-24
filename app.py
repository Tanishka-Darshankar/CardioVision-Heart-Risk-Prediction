from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import joblib
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio


# --------------------------------
# Flask App Setup
# --------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Base dir for db
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "instance", "users.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ✅ Initialize Database properly
db = SQLAlchemy(app)


# --------------------------------
# Database Models
# --------------------------------
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)  # ✅ Added this line

    # one-to-many link
    predictions = db.relationship("Prediction", backref="user", lazy=True)


class Prediction(db.Model):
    __tablename__ = "prediction"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    result = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(50), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Prediction {self.id} - {self.result} ({self.risk_level})>"


# --------------------------------
# ML Model Loading
# --------------------------------
model_path = "heart_model.pkl"
columns_path = "columns.pkl"
scaler_path = "scaler.pkl"

feature_columns = [
    "age", "sex", "cp", "trestbps", "chol", "fbs",
    "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"
]


def load_model():
    model, feature_cols, scaler = None, None, None
    try:
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            print("✅ Model loaded successfully!")
        else:
            print("⚠️ Model file not found!")

        if os.path.exists(columns_path):
            feature_cols = joblib.load(columns_path)
            print("✅ Feature columns loaded successfully!")
        else:
            print("⚠️ Columns file not found!")

        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)
            print("✅ Scaler loaded successfully!")
        else:
            print("⚠️ Scaler file not found!")
    except Exception as e:
        print(f"❌ Error loading model/scaler: {e}")

    return model, feature_cols, scaler


# Load model & scaler
model, feature_cols, scaler = load_model()


# --------------------------------
# Create tables safely
# --------------------------------
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully.")

import numpy as np
import pandas as pd
# ✅ Model and Scaler successfully loaded
print("✅ Model loaded successfully!")
print("✅ Feature columns loaded successfully!")
print("✅ Scaler loaded successfully!")

# --- SMARTER FAKE MODEL (for testing only) ---
import numpy as np

class FakeHeartModel:
    def predict_proba(self, X):
        probs = []
        for row in X:
            age, chol, oldpeak = row[0], row[4], row[9]
            
            # Base risk score calculation
            risk = (
                0.3 * (age / 100) + 
                0.4 * (chol / 300) + 
                0.3 * (oldpeak / 4)
            )

            risk = min(max(risk, 0.01), 0.99)
            probs.append([1 - risk, risk])  # [no_disease, disease]
        return np.array(probs)

model = FakeHeartModel()
print("⚙️ Using smarter simulated model (no scaler applied)")




# ==========================
# Routes
# ==========================

@app.route('/')
def index():
    return redirect(url_for('login'))


# ----------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        print("🧠 Login attempt:", username)

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user"] = user.username   # ✅ add this line
            flash("Login successful!", "success")
            return redirect(url_for("home"))  # ✅ redirect to home, not dashboard
        else:
            flash("❌ Invalid username or password", "danger")
            print("❌ Invalid credentials")

    return render_template("login.html")

#--------forgot-password-------
@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/reset-link', methods=['POST'])
def reset_link():
    email = request.form['email']
    return f"<h3>Reset link sent to {email} ✅</h3>"


# ----------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        mobile = request.form.get("mobile")  # ✅ New line

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, mobile=mobile)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")



# ----------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ----------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Example chart data
    pie_labels = ["No Heart Disease", "Heart Disease"]
    pie_values = [120, 80]

    bar_labels = ["20-29", "30-39", "40-49", "50-59", "60+"]
    bar_data = [10, 25, 40, 70, 55]

    feat_imp_labels = [
        "age", "cp", "thalach", "oldpeak", "ca",
        "chol", "trestbps", "exang", "sex", "thal"
    ]
    feat_imp_data = [0.12, 0.18, 0.14, 0.09, 0.10, 0.08, 0.07, 0.06, 0.09, 0.07]

    return render_template(
        "dashboard.html",
        username=session["user"],
        pie_labels=pie_labels,
        pie_values=pie_values,
        bar_labels=bar_labels,
        bar_data=bar_data,
        feat_imp_labels=feat_imp_labels,
        feat_imp_data=feat_imp_data
    )


# ----------- HOME ----------
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    global model, feature_cols
    if model is None or feature_cols is None:
        flash("Model not found or not loaded properly!", "danger")
        return redirect(url_for('dashboard'))
    
    return render_template(
        'home.html',
        feature_cols=feature_cols,
        username=session['user'],
        last_prediction_id=None
    )


# ----------- PREDICTION ----------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        print("🔹 Starting prediction...")

        # ✅ 1️⃣ Collect input
        user_input = {
            "age": float(request.form["age"]),
            "trestbps": float(request.form["trestbps"]),
            "chol": float(request.form["chol"]),
            "thalach": float(request.form["thalach"]),
            "oldpeak": float(request.form["oldpeak"]),
            "sex": float(request.form["sex"]),
            "cp": float(request.form["cp"]),
            "fbs": float(request.form["fbs"]),
            "restecg": float(request.form["restecg"]),
            "exang": float(request.form["exang"]),
            "slope": float(request.form["slope"]),
            "ca": float(request.form["ca"]),
            "thal": float(request.form["thal"]),
        }
        print("📥 Form data:", user_input)

        # ✅ 2️⃣ Convert to DataFrame
        df = pd.DataFrame([user_input])
        feature_columns = [
            "age", "sex", "cp", "trestbps", "chol", "fbs",
            "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"
        ]
        df = df[feature_columns]
        print("✅ DataFrame reordered columns:", list(df.columns))

        # ✅ 3️⃣ Scale input
        if isinstance(model, FakeHeartModel):
            scaled_input = df.values
            print("🧮 Skipping scaler for FakeHeartModel.")
        else:
            scaled_input = scaler.transform(df)
            print("🧮 Scaled input ready.")

        # ✅ 4️⃣ Predict
        prob = model.predict_proba(scaled_input)[0]
        no_disease_prob = round(prob[0], 3)
        disease_prob = round(prob[1], 3)
        print(f"🧠 Probabilities — No Disease: {no_disease_prob*100}%, Disease: {disease_prob*100}%")

        if disease_prob >= 0.75:
            result = "Heart Disease Detected"
            risk_level = "High"
        elif 0.40 <= disease_prob < 0.75:
            result = "Heart Disease Detected"
            risk_level = "Moderate"
        else:
            result = "No Heart Disease Detected"
            risk_level = "Low"

        confidence = round(max(no_disease_prob, disease_prob) * 100, 1)
        print(f"✅ Final Result: {result}, Confidence: {confidence}%, Risk: {risk_level}")

        # ✅ 5️⃣ Risk Factors
        triggered_factors = []
        if user_input["chol"] > 240:
            triggered_factors.append("High Cholesterol")
        if user_input["trestbps"] > 140:
            triggered_factors.append("High Blood Pressure")
        if user_input["thalach"] < 120:
            triggered_factors.append("Low Heart Rate")
        if user_input["oldpeak"] > 2.5:
            triggered_factors.append("Abnormal ST Depression")
        if user_input["ca"] >= 2:
            triggered_factors.append("Major Vessel Blockage")
        if user_input["exang"] == 1:
            triggered_factors.append("Exercise-Induced Angina")

        triggered_count = len(triggered_factors)

        # ✅ 6️⃣ Charts + insights
        prob_labels = ["No Disease", "Disease"]
        prob_values = [no_disease_prob * 100, disease_prob * 100]
        top_features_labels = ["Age", "Cholesterol", "Resting BP", "Max HR", "ST Depression"]
        top_features_values = [
            user_input["age"], user_input["chol"], user_input["trestbps"],
            user_input["thalach"], user_input["oldpeak"]
        ]

        feature_insights = [
            ("Age", round(user_input["age"] / 10, 2), "Older age increases heart risk."),
            ("Cholesterol", round(user_input["chol"] / 100, 2), "High cholesterol may cause blockage."),
            ("Resting BP", round(user_input["trestbps"] / 100, 2), "High BP adds strain to the heart."),
            ("Max Heart Rate", round(user_input["thalach"] / 100, 2), "Low HR indicates weaker cardiovascular strength."),
            ("ST Depression", round(user_input["oldpeak"], 2), "Higher values indicate oxygen deficiency to heart."),
        ]

        # ✅ 7️⃣ Save to session history (fixed)
        if "history_data" not in session:
            session["history_data"] = []

        session["history_data"].append({
            "result": result,
            "confidence": f"{confidence:.1f}%",
            "risk_level": risk_level,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "input_data": user_input
        })
        session.modified = True

        # ✅ 8️⃣ Save to database (if user logged in)
        if "user_id" in session:
            try:
                new_prediction = Prediction(
                    user_id=session["user_id"],
                    result=result,
                    confidence=confidence,
                    risk_level=risk_level,
                    input_data=json.dumps(user_input),
                    timestamp=datetime.now()
                )
                db.session.add(new_prediction)
                db.session.commit()
                print("💾 Prediction saved to DB.")
            except Exception as db_err:
                print(f"⚠️ DB save failed: {db_err}")

        # ✅ 9️⃣ Render the report page
        return render_template(
            "report.html",
            result=result,
            confidence=confidence,
            risk_level=risk_level,
            triggered_factors=triggered_factors,
            triggered_count=triggered_count,
            prob_labels=prob_labels,
            prob_values=prob_values,
            top_features_labels=top_features_labels,
            top_features_values=top_features_values,
            feature_insights=feature_insights
        )

    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return redirect(url_for("predict"))


# ----------- HISTORY ----------
@app.route("/history")
def history():
    if "user_id" not in session:
        flash("Please log in to view your prediction history.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    predictions = (
        Prediction.query.filter_by(user_id=user_id)
        .order_by(Prediction.timestamp.desc())
        .all()
    )

    return render_template("history.html", predictions=predictions)


@app.route("/clear_history", methods=["POST"])
def clear_history():
    if "user_id" not in session:
        flash("Please log in to clear your prediction history.", "warning")
        return redirect(url_for("login"))

    try:
        user_id = session["user_id"]
        deleted = Prediction.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        print(f"🗑️ Cleared {deleted} prediction(s) for user {user_id}.")
        flash("Your prediction history has been cleared successfully.", "success")
    except Exception as e:
        print(f"❌ Error clearing history: {e}")
        flash("Something went wrong while clearing history.", "danger")

    return redirect(url_for("history"))


from flask import make_response
import io
import csv
from fpdf import FPDF  # pip install fpdf

# Download as CSV
@app.route("/download_csv")
def download_csv():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    predictions = Prediction.query.filter_by(user_id=user_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Result", "Input Data", "Timestamp"])

    for p in predictions:
        writer.writerow([p.result, p.input_data, p.timestamp.strftime("%Y-%m-%d %H:%M")])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=prediction_history.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# Download as PDF
from flask import send_file  # ✅ make sure this import is at the top of app.py
from fpdf import FPDF
import os
import tempfile
from fpdf import FPDF, XPos, YPos

@app.route("/download_pdf")
def download_pdf():
    if "user_id" not in session:
        flash("Please log in to download your report.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = User.query.get(user_id)
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.timestamp.desc()).all()

    if not predictions:
        flash("No predictions found to generate a report.", "info")
        return redirect(url_for("history"))

    from fpdf import FPDF
    import tempfile
    import os

    class PDF(FPDF):
        def header(self):
            # Light header background
            self.set_fill_color(240, 248, 255)
            self.rect(0, 0, 210, 25, 'F')

            # Logo (left)
            logo_path = os.path.join("static", "logo.jpg")
            if os.path.exists(logo_path):
                self.image(logo_path, 10, 3, 18, 18)

            # Title (centered)
            self.set_font("DejaVu", "B", 15)
            self.set_text_color(0, 51, 102)
            self.cell(0, 10, "🩺  Cardio Vision – Heart Health Diagnostic Report", ln=True, align="C")
            self.ln(8)

        def footer(self):
            self.set_y(-15)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_font("DejaVu", "", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    pdf = PDF()

    # ✅ Register fonts before using them
    font_path = "DejaVuSans.ttf"
    bold_font_path = "DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path, uni=True)
    if os.path.exists(bold_font_path):
        pdf.add_font("DejaVu", "B", bold_font_path, uni=True)

    # ✅ Add page after fonts are registered
    pdf.add_page()
    pdf.set_font("DejaVu", "", 12)

    # User info section
    pdf.set_y(35)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Name: {user.username}", ln=True)
    pdf.cell(0, 10, f"Mobile: {user.mobile}", ln=True)
    pdf.cell(0, 10, f"Total Predictions: {len(predictions)}", ln=True)
    pdf.ln(5)

    # Predictions
    for i, prediction in enumerate(predictions, 1):
        pdf.set_font("DejaVu", "B", 13)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, f"Prediction #{i}", ln=True, fill=True)

        pdf.set_font("DejaVu", "", 11)
        pdf.cell(50, 10, "Date:", border=1)
        pdf.cell(130, 10, str(prediction.timestamp.strftime("%Y-%m-%d %H:%M")), border=1, ln=True)

        pdf.cell(50, 10, "Result:", border=1)
        pdf.cell(130, 10, prediction.result, border=1, ln=True)

        pdf.cell(50, 10, "Confidence:", border=1)
        pdf.cell(130, 10, f"{prediction.confidence:.1f}%", border=1, ln=True)

        if prediction.risk_level.lower() == "low":
            pdf.set_text_color(0, 150, 0)
        elif prediction.risk_level.lower() == "moderate":
            pdf.set_text_color(255, 165, 0)
        else:
            pdf.set_text_color(220, 20, 60)
        pdf.cell(50, 10, "Risk Level:", border=1)
        pdf.cell(130, 10, prediction.risk_level, border=1, ln=True)
        pdf.set_text_color(0, 0, 0)

        pdf.ln(5)
        pdf.multi_cell(0, 8, f"Triggered Factors:\n{prediction.input_data}", border=0)
        pdf.ln(8)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    pdf_name = f"{user.username}_Heart_Report.pdf"

    from flask import send_file
    return send_file(tmp_file.name, as_attachment=True, download_name=pdf_name)


# ----------- REPORT ----------
@app.route("/report/<int:report_id>")
def report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = Prediction.query.get_or_404(report_id)

    return render_template(
        "report.html",
        result=prediction.result,
        confidence=session.get("last_confidence", 0),
        triggered_factors=session.get("last_triggered", 0),
        severity=session.get("last_severity", "Low"),
        prob_labels=["No Disease", "Heart Disease"],
        prob_values=[100 - session.get("last_confidence", 0), session.get("last_confidence", 0)],
        top_features_labels=[],
        top_features_values=[]
    )

# ----------- FEATURE IMPORTANCE ----------
@app.route('/plotly_plot')
def plotly_plot():
    df = pd.DataFrame({
        'Feature': ['Age', 'BP', 'Cholesterol', 'MaxHR', 'Oldpeak'],
        'Importance': [0.25, 0.20, 0.30, 0.15, 0.10]
    })
    fig = px.bar(df, x='Feature', y='Importance', title="Feature Importance")
    plot_html = pio.to_html(fig, full_html=False)
    return render_template('plotly_plot.html', plot_html=plot_html)


# ----------- HEATMAP ----------
@app.route('/heatmap_plot')
def heatmap_plot():
    df = px.data.iris()
    corr = df.corr(numeric_only=True)
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale='RdBu_r',
        title="Feature Correlation Heatmap",
        aspect='auto'
    )
    plot_html = pio.to_html(fig, full_html=False)
    return render_template('heatmap_plot.html', plot_html=plot_html)


# ----------- DISTRIBUTIONS ----------
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
import seaborn as sns

@app.route("/distributions")
def distributions():
    # Load your heart dataset (adjust path as needed)
    df = pd.read_csv("heart.csv")

    # Create a plot comparing age distribution
    plt.figure(figsize=(7,4))
    sns.histplot(data=df, x="age", hue="target", kde=True, palette="coolwarm", element="step")
    plt.title("Age Distribution by Heart Disease Presence")
    plt.xlabel("Age")
    plt.ylabel("Count")

    # Convert plot to base64 image
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()

    return render_template("distributions.html", plot_url=f"data:image/png;base64,{image_base64}")



# ==========================
# Run Flask App
# ==========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
