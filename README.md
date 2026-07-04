## Steam Library & Achievement Dashboard

## Video Demo: <URL HERE>

## Description:

Steam Library & Achievement Dashboard is a Flask-based web application that lets a user connect their Steam account, pull their real game library directly from the Steam Web API, and manage that library through a personal dashboard. Instead of relying on Steam's own (fairly cluttered) profile page, this project gives the user a clean, filterable view of their games, how long they've played each one, and a manually-tracked completion status for each title (Not Started, Playing, Completed, Dropped), and track your achievments of every game in your library. It was built as my CS50x final project using Flask, Python, SQLite, and the cs50 library for database access, and it borrows the authentication pattern I first learned while building the Finance problem set :) 

The core idea behind the project came from a simple frustration: Steam tells you what you own and how long you played it, but it doesn't let you organize your backlog in any meaningful way And because of this so many time i stop play games for a long time :( 

So i made this web app to solve this problem .

---

## How it works

When a user registers, they provide a username, password, and their 64-bit Steam ID (SteamID64, found in their Steam profile URL). The app hashes the password with werkzeug.security before storing it — no plaintext passwords ever touch the database. Once logged in, the user lands on two main views:


Dashboard (/) — a summary view showing the user's games ordered by playtime, meant to give a quick "here's what I've been playing" snapshot.
Library (/games) — the full library view, with filter buttons to narrow the list down by completion status, and a "Sync Games" button that pulls fresh data from Steam on demand.


Neither of these routes talks to Steam directly. They only read from the local steam_games table. Fetching from Steam is a deliberately separate action: the library page includes a "Sync Games" button that the user clicks whenever they want fresh data, which hits /games/sync. This split was one of the more important design decisions in the project. My first version had the /games route fetch from Steam and render the page in the same function, which meant every single page load re-hit the Steam API and re-ran insert logic, even when the user just wanted to look at data that hadn't changed. Splitting sync out into its own route means the library page is fast (pure database read), and a sync only happens when the user explicitly asks for one.

Because a sync can run more than once for the same user, the app needed upsert logic: for every game Steam returns, it checks whether that game_appid already exists for the current user. If it does, the row is updated (name, playtime, header image) rather than duplicated. If it doesn't, a new row is inserted. Crucially, the sync never touches the status column, since that's data the user set manually and Steam has no knowledge of it — overwriting it on every sync would erase the user's own tracking work.

---

## Files


**app.py** — the entire application logic lives here. It defines all routes: / (dashboard), /login, /register, /games, /games/sync, /games/update_status/<appid>, and /logout. It handles session management via Flask-Session, builds the Steam API request URL dynamically per user (based on their stored Steam ID), parses the JSON response, and runs the upsert logic described above. It also sets no-cache headers on every response (after_request) so that logged-out users can't hit the browser back button and see cached authenticated pages — **this pattern I carried over from Finance :)**

**helpers.py** — contains the @login_required decorator, **which is also carried over from the Finance problem set :)** 

**database.db** — the SQLite database with two tables: users (id, username, hash, steam_id) and steam_games (id, user_id, app_id, game_name, playtime_forever, img_icon_url, status, achievements_unlocked and achievements_total).

**templates/layout.html** — the shared base template (nav bar, flash messages, Bootstrap styling and little css) that every other page extends.

**templates/dashboard.html** — renders the summary view of the user's synced library.

**templates/games.html** — the main library view: filter buttons by status, and a small form per game to update its status, each posting to /games/update_status/<appid>.

**templates/login.html** / **templates/register.html** — standard authentication forms, with registration also collecting the user's Steam ID.

**static/styles.css** — little css for ( html, nav, body, forms, and edit some styles from bootstrap )

**.env** — holds the STEAM_API_KEY, excluded from version control via .gitignore so the key is never pushed to GitHub.
