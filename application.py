import os
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    history = db.execute("SELECT symbol, shares, price FROM transactions WHERE id=:id", id=session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id=:id_", id_=session["user_id"])

    return render_template("index.html", history=history, cash=cash[0]["cash"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Sorry, symbol field is empty", 400)
        if not request.form.get("shares"):
            return apology("Sorry, shares field is empty", 400)

        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("Incorrect symbol", 404)

        if int(request.form.get("shares")) <= 0:
            return apology("Shares must be a positive integer", 400)

        if (db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"]))[0]["cash"] < float(quote["price"]) * float(request.form.get("shares")):
            return apology("OOOPS, you have not got sooooo much money")


        total_price = float(quote["price"]) * int(request.form.get("shares"))

        db.execute("UPDATE users SET cash = cash - :total_price WHERE id = :id_", total_price = total_price, id_ = session["user_id"])
        db.execute("INSERT INTO transactions ('id', 'symbol', 'shares', 'price') VALUES (:user_id, :symbol, :shares, :price)", user_id = session["user_id"], symbol = request.form.get("symbol"), shares = request.form.get("shares"), price = quote["price"])

        flash("Bought!")

        return redirect("/")


    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT symbol, shares, price FROM transactions WHERE id=:user_id", user_id=session["user_id"])
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("Incorrect symbol", 404)

        else:
            return render_template("quoted.html", quote=quote)

    # GET method
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":

        # Ensure username exists and password is correct
        if not request.form.get("username"):
            return apology("Sorry, you must provide username", 403)

        elif not request.form.get("password"):
            return apology("Sorry, you must provide password", 403)

        # Ensure passwords are match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Sorry, incorrect password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) > 0:
            return apology("Sorry, this username is already exist", 400)
        hash=generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hash)

        flash("Registred!")

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Sorry, symbol field is empty", 400)
        if not request.form.get("shares"):
            return apology("Sorry, shares field is empty", 400)

        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("Incorrect symbol", 404)

        if int(request.form.get("shares")) <= 0:
            return apology("Shares must be a positive integer", 400)


        total_price = float(quote["price"]) * int(request.form.get("shares"))

        db.execute("UPDATE users SET cash = cash + :total_price WHERE id = :id_", total_price = total_price, id_ = session["user_id"])
        db.execute("INSERT INTO transactions ('id', 'symbol', 'shares', 'price') VALUES (:user_id, :symbol, :shares, :price)", user_id = session["user_id"], symbol = request.form.get("symbol"), shares = request.form.get("shares"), price = quote["price"])

        flash("Sold!")

        return redirect("/")
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)



# Сделать таблицы sell и buy и в продаже сделать список названий акций, которые можно продать
# которые можно продать, и условие: количество <= сколько есть у пользователя