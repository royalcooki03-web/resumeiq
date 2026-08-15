from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import sqlite3, os, re
from datetime import datetime
from io import BytesIO

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"]=5*1024*1024
UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER","uploads")
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
DB="resumeiq.db"

ROLE_SKILLS={
"Python Developer":["python","flask","django","sql","git","github","pandas","numpy"],
"Data Analyst":["python","sql","excel","power bi","pandas","numpy","matplotlib","data analysis"],
"AI/ML Engineer":["python","machine learning","deep learning","tensorflow","pytorch","scikit-learn","numpy","pandas"],
"Web Developer":["html","css","javascript","react","node.js","sql","git"],
"Software Developer":["python","java","c++","sql","git","github","problem solving"],
"General":["communication","teamwork","problem solving","leadership"]
}
SKILLS=sorted(set(sum(ROLE_SKILLS.values(),[])+["typescript","angular","mongodb","postgresql","docker","aws","azure","seaborn","artificial intelligence","ai","communication skills"]))

def db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def init_db():
    con=db()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created_at TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS analyses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,filename TEXT,job_role TEXT,score INTEGER,
        matched TEXT,missing TEXT,suggestions TEXT,created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id))""")
    con.commit();con.close()

def current_user():
    if "user_id" not in session:return None
    con=db();u=con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone();con.close();return u

def extract(path):
    r=PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in r.pages)

def skills(text):
    t=re.sub(r"\s+"," ",text.lower()); out=[]
    for s in SKILLS:
        if re.search(r"(?<!\w)"+re.escape(s)+r"(?!\w)",t):out.append(s)
    return out

def analyze(text,role):
    target=ROLE_SKILLS.get(role,ROLE_SKILLS["General"]); found=skills(text)
    matched=[s for s in target if s in found]; missing=[s for s in target if s not in found]
    score=round(len(matched)/len(target)*100)
    sug=[]
    if not re.search(r"\b(summary|profile|objective)\b",text,re.I):sug.append("Add a concise professional summary at the top.")
    if not re.search(r"\b(project|projects)\b",text,re.I):sug.append("Add 2–3 relevant projects with technologies and measurable results.")
    if not re.search(r"\b(experience|internship|work experience)\b",text,re.I):sug.append("Add internship, training, freelance, or practical experience.")
    if not re.search(r"\b(education|qualification|degree|diploma)\b",text,re.I):sug.append("Clearly mention your education and qualifications.")
    if missing:sug.append("Add missing target skills only if you genuinely know them.")
    if len(text.split())<180:sug.append("Your resume is short. Add achievements, projects, and relevant details.")
    sug.append("Use strong action verbs and quantify achievements where possible.")
    return score,matched,missing,sug

@app.context_processor
def inject():
    return {"user":current_user()}

@app.route("/")
def home():
    return redirect(url_for("dashboard")) if current_user() else redirect(url_for("login"))

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip();email=request.form["email"].strip().lower();password=request.form["password"]
        if len(password)<6:flash("Password must contain at least 6 characters.","error");return redirect(url_for("register"))
        con=db()
        try:
            cur=con.execute("INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)",
                (name,email,generate_password_hash(password),datetime.now().strftime("%d %b %Y")))
            con.commit();session["user_id"]=cur.lastrowid;con.close()
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            con.close();flash("An account with this email already exists.","error")
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower();password=request.form["password"]
        con=db();u=con.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone();con.close()
        if u and check_password_hash(u["password"],password):
            session["user_id"]=u["id"];return redirect(url_for("dashboard"))
        flash("Invalid email or password.","error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear();return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not current_user():return redirect(url_for("login"))
    con=db();rows=con.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall()
    total=len(rows);avg=round(sum(r["score"] for r in rows)/total) if total else 0
    con.close()
    return render_template("dashboard.html",rows=rows,total=total,avg=avg)

@app.route("/analyze",methods=["POST"])
def analyze_resume():
    if not current_user():return redirect(url_for("login"))
    f=request.files.get("resume");role=request.form.get("job_role","General")
    if not f or not f.filename.lower().endswith(".pdf"):flash("Please upload a PDF resume.","error");return redirect(url_for("dashboard"))
    filename=secure_filename(f.filename);path=os.path.join(UPLOAD_FOLDER,filename);f.save(path)
    try:
        text=extract(path)
        if not text.strip():raise ValueError("No readable text found in this PDF.")
        score,matched,missing,sug=analyze(text,role)
        con=db();cur=con.execute("""INSERT INTO analyses(user_id,filename,job_role,score,matched,missing,suggestions,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",(session["user_id"],filename,role,score,", ".join(matched),", ".join(missing),"||".join(sug),datetime.now().strftime("%d %b %Y, %I:%M %p")))
        aid=cur.lastrowid;con.commit();con.close()
        return redirect(url_for("result",aid=aid))
    except Exception as e:
        flash("Could not analyze this PDF: "+str(e),"error");return redirect(url_for("dashboard"))

def get_analysis(aid):
    con=db();r=con.execute("SELECT * FROM analyses WHERE id=? AND user_id=?",(aid,session["user_id"])).fetchone();con.close();return r

@app.route("/result/<int:aid>")
def result(aid):
    if not current_user():return redirect(url_for("login"))
    r=get_analysis(aid)
    if not r:return "Analysis not found",404
    d=dict(r);d["matched"]=[x for x in d["matched"].split(", ") if x];d["missing"]=[x for x in d["missing"].split(", ") if x];d["suggestions"]=[x for x in d["suggestions"].split("||") if x]
    return render_template("result.html",data=d)

@app.route("/history")
def history():
    if not current_user():return redirect(url_for("login"))
    con=db();rows=con.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall();con.close()
    return render_template("history.html",rows=rows)

@app.route("/delete/<int:aid>",methods=["POST"])
def delete(aid):
    if not current_user():return redirect(url_for("login"))
    con=db();con.execute("DELETE FROM analyses WHERE id=? AND user_id=?",(aid,session["user_id"]));con.commit();con.close();return redirect(url_for("history"))

@app.route("/profile")
def profile():
    if not current_user():return redirect(url_for("login"))
    return render_template("profile.html")

@app.route("/report/<int:aid>")
def report(aid):
    if not current_user():return redirect(url_for("login"))
    r=get_analysis(aid)
    if not r:return "Not found",404
    text=f"""RESUMEIQ - RESUME ANALYSIS REPORT

Resume: {r['filename']}
Target Role: {r['job_role']}
ATS Score: {r['score']}/100
Date: {r['created_at']}

MATCHED SKILLS
{r['matched'] or 'None'}

MISSING SKILLS
{r['missing'] or 'None'}

IMPROVEMENT SUGGESTIONS
{chr(10).join('• '+x for x in r['suggestions'].split('||'))}
"""
    return send_file(BytesIO(text.encode()),as_attachment=True,download_name="ResumeIQ_Report.txt",mimetype="text/plain")

@app.get("/health")
def health():
    return {"status":"ok"}

if __name__=="__main__":
    init_db();app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)
