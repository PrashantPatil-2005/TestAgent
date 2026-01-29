from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = 'ai_web_tester_secret_key_2024'

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Store user in session
        session['username'] = username
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    username = session.get('username', 'Guest')
    return render_template("dashboard.html", username=username)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        return render_template("search_results.html", query=query)
    return render_template("search.html")

@app.route("/form-step-1", methods=["GET", "POST"])
def step1():
    if request.method == "POST":
        session['form_step1'] = request.form.get('name', '')
        return redirect("/form-step-2")
    return render_template("multistep_step1.html")

@app.route("/form-step-2", methods=["GET", "POST"])
def step2():
    if request.method == "POST":
        session['form_step2'] = request.form.get('email', '')
        return redirect("/form-step-3")
    return render_template("multistep_step2.html")

@app.route("/form-step-3")
def step3():
    name = session.get('form_step1', 'N/A')
    email = session.get('form_step2', 'N/A')
    return render_template("multistep_step3.html", name=name, email=email)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
