from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    redirect,
)
from flask_session import Session
import pprint
import mpld3
import plotly.tools as tls


from kos_api import KOSApi, visualize_timetable_html

app = Flask(__name__)

app.config["SESSION_TYPE"] = "filesystem"  # Store sessions on the server
app.config["SESSION_PERMANENT"] = False  # Optional: non-permanent sessions
app.config["SESSION_FILE_DIR"] = "./flask_session"  # Where to store session files
Session(app)

app.secret_key = "your_secret_key"


@app.route("/")
def home():
    kos: KOSApi | None = session.get("kos")
    if kos is None:
        return render_template("home.html")

    sem_courses = kos.get_courses()
    course_codes = dict()
    for sem, courses in sem_courses.items():
        course_codes[sem] = map(lambda course: course["code"], courses)
    return render_template(
        "home.html",
        user_data=session.get("kos"),
        pformat=pprint.pformat,
        tv=visualize_timetable_html,
        courses=kos.get_courses(),
        course_codes=course_codes.items(),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        kos = KOSApi(username, password)

        session["kos"] = kos
        return redirect("/")

    return render_template("login.html")


@app.route("/timetable")
def timetable():
    kos = session.get("kos")
    if kos is None:
        return redirect("/login")
    courses = request.args.get("courses").split(",")
    semester = request.args.get("semester")

    return render_template(
        "timetable.html",
        timetable=visualize_timetable_html(kos.get_schedule_courses(courses, semester)),
    )


app.run(debug=True)
