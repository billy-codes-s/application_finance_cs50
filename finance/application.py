import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import math
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
    allstocks = db.execute("SELECT * FROM ownings where person_id = ?", session["user_id"])
    print(allstocks) ## this is a json
    final_data = []
    valuation = 0
    for stocks in allstocks:
        small_dick = {"symbol" :0, "name" : 0, "quantity" : 0, "price" : 0, "total" : 0}

        current_data = lookup(stocks["stock_symb"])
        small_dick["symbol"] = stocks["stock_symb"]
        small_dick["name"] = current_data["name"]
        small_dick["quantity"] = stocks["stock_q"]
        small_dick["price"] = current_data["price"]
        small_dick["total"] = current_data["price"] * stocks["stock_q"]
        valuation =valuation + current_data["price"] * stocks["stock_q"]
        final_data.append(small_dick)

    print(final_data)
    available =db.execute("select cash from users where id = ?", session["user_id"])[0]["cash"]

    last_row = {"symbol" :"cash", "name" : "", "quantity" : "", "price" : 0, "total" : available}

    foot = {"symbol" :"", "name" : "", "quantity" : "", "price" : 0, "total" :  valuation+available}
    final_data.append(last_row)
    final_data.append(foot)
    return render_template("stocks.html", ownings = final_data)




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""


    if request.method == "GET":

        return render_template("buy.html")## ok good

    if request.method == "POST":
        available = db.execute("select cash from users where id = ?", session["user_id"])[0]["cash"]

        if not request.form.get("shares"):
            return apology("please enter valid number of shares", 400)

        try:
            what = float(request.form.get("shares"))

        except ValueError:
            return apology("please enter valid number of shares", 400)

        if not what.is_integer():
            return apology("please enter valid number of shares", 400)



        stock = lookup(request.form.get("symbol"))

        if not stock:
            return apology("Wrong symbol")
            ## this is perfect
        if int(request.form.get("shares")) < 1:
            return apology("Please enter valid stock number")


        user_stock = db.execute("select * from ownings where person_id = ?", session["user_id"])


        for holdings in user_stock:
            print(holdings["stock_symb"])
            if str(stock["symbol"]) != str(holdings["stock_symb"]):
                continue
            ## this is good, if it is not there skip


            else:
                old_quantity = holdings["stock_q"]
                new_quantity = old_quantity + int(request.form.get("shares"))
                total_taken = stock["price"]*int(request.form.get("shares"))
                if total_taken > available:
                    return apology("bro you broke")
                db.execute("update ownings set stock_q = ? where stock_symb =? and person_id = ?", new_quantity,stock["symbol"],session["user_id"] )
                db.execute("update users set cash = cash - ? where id = ?", total_taken, session["user_id"])
                return redirect("/")

        ### so if it is a new stock
        total_taken = stock["price"]*int(request.form.get("shares"))
        if total_taken > available:
            return apology("bro you broke")
        db.execute("Insert into ownings(stock_symb, stock_q, person_id) values (?,?,?)",stock["symbol"],request.form.get("shares"),session["user_id"])
        db.execute("update users set cash = cash - ? where id = ?", total_taken, session["user_id"])
        return redirect("/")





@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":
        stock = lookup(str(request.form.get("symbol")))
        ##  a list with an empty dic is not void
        if not stock:
            return apology("wrong symbol")
        return render_template("quoted.html", ownings = [stock])

    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    usernames = db.execute("select * from users")

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        if not request.form.get("password"):
            return apology("must provide password", 400)

        if str(request.form.get("password")) != str(request.form.get("confirmation")):
            return apology("repeat password", 400)

        for users in usernames:
            if users["username"] == request.form.get("username"):
                return apology("unavailable username")

        db.execute("Insert into users(username, hash) values(?,?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        return redirect("/login")




    if request.method == "GET":
        return render_template("register.html")


    return apology("Try again, unclear", 502)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks = db.execute("select * from ownings where person_id = ?", session["user_id"])

    if request.method == "GET":
        return render_template("sell.html", options = stocks)

    if request.method == "POST":
        target_stock = request.form.get("symbol")
        target_q = request.form.get("shares")

        if not target_q:
            return apology("bro, cmon man")

        try:
            what = float(request.form.get("shares"))
            if what < 1:
                return apology("bro, cmon man")

        except ValueError:
            return apology("please enter valid number of shares", 400)



        target_data = db.execute("select * from ownings where person_id = ? and stock_symb = ?", session["user_id"],str(target_stock))[0]
        stock_data = lookup(target_data["stock_symb"])
        new_q = target_data["stock_q"] - int(target_q)

        total_for_transfer = int(target_q) * stock_data["price"]


        if new_q < 0:
            return apology("bro, cmon man")

        if new_q == 0:
            db.execute("delete from ownings where person_id = ? and stock_symb = ?", session["user_id"], target_stock)
            ##this deletes the owning
            ## gives teh cash back
        else:
            db.execute("update ownings set stock_q = ? where stock_symb =? and person_id = ?", new_q, target_stock,session["user_id"])

        db.execute("update users set cash = cash + ? where id = ?", total_for_transfer, session["user_id"])

        print(target_data)
        return redirect("/")







def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
