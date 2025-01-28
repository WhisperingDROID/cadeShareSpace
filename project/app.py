import os
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    session,
    flash,
    redirect,
    url_for,
    abort,
    jsonify,
)
from project.models import db, User, Post  # Import models directly from models.py

basedir = Path(__file__).resolve().parent

# Configuration
DATABASE = "shareSpace.db"
USERNAME = "admin"
PASSWORD = "admin"
SECRET_KEY = "change_me"
url = os.getenv("DATABASE_URL", f"sqlite:///{Path(basedir).joinpath(DATABASE)}")

if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URI = url
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create and initialize a new Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
app.secret_key = SECRET_KEY

# Initialize SQLAlchemy with the app
db.init_app(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in.")
            return jsonify({"status": 0, "message": "Please log in."}), 401
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    """Searches the database for entries, then displays them."""
    entries = db.session.query(Post).all()
    return render_template("index.html", entries=entries)


@app.route("/add", methods=["POST"])
def add_entry():
    """Adds a new post to the database."""
    if not session.get("logged_in"):
        abort(401)
    user = db.session.query(User).filter_by(name=session.get("username")).first()
    if not user:
        abort(401, description="User not found")

    new_entry = Post(title=request.form["title"], text=request.form["text"], user_id=user.id)
    db.session.add(new_entry)
    db.session.commit()
    flash("New entry was successfully posted")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login/authentication/session management."""
    error = None
    if request.method == "POST":
        user = db.session.query(User).filter_by(name=request.form["username"]).first()
        if not user or user.password != request.form["password"]:
            error = "Invalid username or password"
        else:
            session["logged_in"] = True
            session["username"] = user.name  # Store username in session
            flash("You were logged in")
            return redirect(url_for("index"))
    return render_template("login.html", error=error)


@app.route("/newuser", methods=["GET", "POST"])
def new_user():
    """Allows the creation of a new user."""
    if request.method == "POST" and request.form.get("password") and request.form.get("username"):
        new_user = User(name=request.form["username"], password=request.form["password"])
        try:
            db.session.add(new_user)
            db.session.commit()
            session["logged_in"] = True
            session["username"] = new_user.name  # Store username in session
            flash("New User Created")
            return redirect(url_for("index"))
        except Exception as e:
            return render_template("newuser.html", error="Error when adding user: " + str(e))
    return render_template("newuser.html")


@app.route("/user/<int:user_id>")
def user_profile(user_id):
    """Displays a user's profile and their posts."""
    user = db.session.query(User).get(user_id)
    if not user:
        abort(404, description="User not found")
    posts = db.session.query(Post).filter_by(user_id=user_id).all()
    return render_template("user_profile.html", user=user, posts=posts)


@app.route("/logout")
def logout():
    """Logs out the current user."""
    session.pop("logged_in", None)
    session.pop("username", None)
    flash("You were logged out")
    return redirect(url_for("index"))


@app.route("/delete/<int:post_id>", methods=["GET"])
@login_required
def delete_entry(post_id):
    """Deletes a post from the database."""
    result = {"status": 0, "message": "Error"}
    try:
        db.session.query(Post).filter_by(id=post_id).delete()
        db.session.commit()
        result = {"status": 1, "message": "Post Deleted"}
        flash("The entry was deleted.")
    except Exception as e:
        result = {"status": 0, "message": repr(e)}
    return jsonify(result)


@app.route("/search/", methods=["GET"])
def search():
    """Search for posts."""
    query = request.args.get("query")
    entries = db.session.query(Post).all()
    if query:
        return render_template("search.html", entries=entries, query=query)
    return render_template("search.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
