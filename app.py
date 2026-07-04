import os, requests, json
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash   
from helpers import login_required
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()
steam_api_key = os.environ.get("STEAM_API_KEY")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///database.db")

@app.route("/")
@login_required
def index():

    user_data = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    current_username = user_data[0]["username"]

    games_list = db.execute(
        "SELECT game_appid, game_name, playtime_forever, img_icon_url, achievements_unlocked, achievements_total, status "
        "FROM steam_games WHERE user_id = ? ORDER BY playtime_forever DESC",
        session["user_id"]
    )

    return render_template("dashboard.html", username=current_username, games=games_list)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Please fill out all fields.")
            return redirect("/login")
        db_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(db_user) != 1 or not check_password_hash(db_user[0]["hash"], password):
            flash("Invalid username or password.")
            return redirect("/login")
        else:
            session["user_id"] = db_user[0]["id"]
            return redirect("/")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        steam_id = request.form.get("steam_id")

        if not username or not password or not confirmation or not steam_id:
            flash("Please fill out all fields.")
            return redirect("/register")

        if password != confirmation:
            flash("Passwords do not match.")
            return redirect("/register")
        
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            flash("Username already exists.")
            return redirect("/register")
        

        
        db.execute("INSERT INTO users (username, hash, steam_id) VALUES (?, ?, ?)", username, generate_password_hash(password), steam_id)

        flash("Registration successful. Please log in.")
        return redirect("/login")

    return render_template("register.html")

@app.route("/games")
@login_required
def games():
    games_list = db.execute(
        "SELECT game_appid, game_name, playtime_forever, img_icon_url, achievements_unlocked, achievements_total, status "
        "FROM steam_games WHERE user_id = ? ORDER BY playtime_forever DESC",
        session["user_id"]
    )
    if format(request.args.get("status")):
        current_status = request.args.get("status")
        if current_status == "not_started":
            games_list = [game for game in games_list if game["status"] == "not_started"]
        elif current_status == "playing":
            games_list = [game for game in games_list if game["status"] == "playing"]
        elif current_status == "completed":
            games_list = [game for game in games_list if game["status"] == "completed"]
        elif current_status == "dropped":
            games_list = [game for game in games_list if game["status"] == "dropped"]
        else:
            games_list = games_list
    return render_template("games.html", games=games_list)


@app.route("/games/sync")
@login_required
def sync_games():
    user = db.execute("SELECT steam_id FROM users WHERE id = ?", session["user_id"])
    steam_id = user[0]["steam_id"] if user else None
 
    if not steam_id:
        flash("Link your Steam account first")
        return redirect("/games")
 
    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={steam_api_key}&steamid={steam_id}&format=json&include_appinfo=true"
    )
 
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        flash("Couldn't reach Steam right now, try again later")
        return redirect("/games")
    except ValueError:
        flash("Steam returned an unexpected response")
        return redirect("/games")
 
    games_list = data.get("response", {}).get("games", [])
 
    if not games_list:
        flash("No games found on your Steam profile")
        return redirect("/games")
 
    existing_rows = db.execute(
        "SELECT game_appid FROM steam_games WHERE user_id = ?", session["user_id"]
    )
    existing_appids = {row["game_appid"] for row in existing_rows}
 
    synced_appids = set()
 
    for game in games_list:
        appid = game["appid"]
        name = game.get("name", "Unknown Game")
        playtime = round(game.get("playtime_forever", 0) / 60, 1)
        img_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
 
        synced_appids.add(appid)
 
        if appid in existing_appids:
            db.execute(
                "UPDATE steam_games SET game_name = ?, playtime_forever = ?, img_icon_url = ? "
                "WHERE user_id = ? AND game_appid = ?",
                name, playtime, img_url, session["user_id"], appid
            )
        else:
            db.execute(
                "INSERT INTO steam_games (user_id, game_appid, game_name, playtime_forever, img_icon_url) "
                "VALUES (?, ?, ?, ?, ?)",
                session["user_id"], appid, name, playtime, img_url
            )
    flash("Games synced successfully")
    return redirect("/games")

@app.route("/games/update_status/<int:appid>", methods=["POST"])
@login_required
def update_status(appid):
    new_status = request.form.get("status")

    allowed_statuses = ["not_started", "playing", "completed", "dropped"]
    if new_status not in allowed_statuses:
        return redirect(url_for("games"))

    db.execute(
        "UPDATE steam_games SET status = ? WHERE game_appid = ? AND user_id = ?",
        new_status, appid, session["user_id"]
    )

    return redirect(url_for("games"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")