from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from datetime import datetime,timezone,timedelta

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    porfolio = db.execute("SELECT * FROM porfolio WHERE id = :id", id=session["user_id"])

    if not porfolio: #還沒開始買賣過
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        profolio = []
        temp_d = {}
        temp_d["cash"] = '%.2f' % cash[0]["cash"]
        porfolio.append(temp_d)
        return render_template("index.html", porfolio=porfolio)
    elif len(porfolio) > 0: #已經買賣過了,有持股紀錄

        stock = [] # 為了要存porfolio裡買過的股票的資訊 [{'name':''}, {'symbol':''}, {'price': }]

        # 把porfolio list裡,holding_share = 0的list通通拿掉(持股=0的資料拿掉)
        porfolio = [item for item in porfolio if (item["holding_share"] != 0)]

        # 若拿掉之後,porfolio裡面沒半個資料了
        if len(porfolio) == 0:
            cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
            profolio = []
            temp_d = {}
            temp_d["cash"] = '%.2f' % cash[0]["cash"]
            porfolio.append(temp_d)
            return render_template("index.html", porfolio=porfolio)

        for i in range(0, len(porfolio)):
            stock.append(lookup(porfolio[i]["symbol"]))

        # 把stock list裡的dict新增進porfolio list的dict裡
        for i in range(0, len(porfolio)):
            porfolio[i]["name"] = stock[i]["name"]
            porfolio[i]["price"] = '%.2f' % stock[i]["price"]
            porfolio[i]["total"] = '%.2f' % (stock[i]["price"] * porfolio[i]["holding_share"])
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        porfolio[0]["cash"] = '%.2f' % cash[0]["cash"]

        return render_template("index.html", porfolio=porfolio)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "GET":
        return render_template("buy.html")
    elif request.method == "POST":
        stock = lookup(request.form.get("stock_symbol"))
        # lookup輸入symbol之後,會回傳該股票的list of dict, dict的內容有name, symbol, price,且都是str資料型態

        # 檢查有沒有這檔股票
        if not stock:
            return apology("can't buy this stock!", "there is no such company ")

        # 檢查使用者輸入的share值有沒有來亂
        if not request.form.get("share") or int(request.form.get("share")) <= 0:
            return apology("Do not play with me", "Shares must be positive")
        share = int(request.form.get("share"))

        money = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        # db.execute裡的第一個指令若是SELECT,會回傳一個list of dict,所以要先選擇list裡的第一項[0],才能取用dict裡面的資料,且資料是str型態

        # 檢查使用者錢夠不夠買這檔股票,若不夠錢就停在這關,夠的話接著下去
        if  float(money[0]["cash"]) < float(stock["price"]) * share:
            return apology("you can't afford it!", "poor guy")

        # 儲存賣賣紀錄
        utc_dt = datetime.utcnow() # 以utc時間型式儲存在資料庫裡
        db.execute("INSERT INTO history (id, symbol, stock_name, shares, price, total, datetime) VALUES (:id, :symbol, :stock_name, :shares, :price, :total, :datetime)",
                    id=session["user_id"], symbol=stock["symbol"], stock_name=stock["name"], shares=share, price=float(stock["price"]), total=share*float(stock["price"]),
                    datetime=utc_dt)

        # 更新使用者的現金
        db.execute("UPDATE users SET cash = cash - :purchase WHERE id = :id", id = session["user_id"], purchase = share*float(stock["price"]))

        # 將使用者買過的該股票叫出來
        user_stocks = db.execute("SELECT holding_share FROM porfolio WHERE id = :id AND symbol = :symbol", id = session["user_id"], symbol = stock["symbol"])
        if not user_stocks: # 若沒買過這檔股票,就新增一欄去記錄持股
            db.execute("INSERT INTO porfolio (id, symbol, holding_share) VALUES (:id, :symbol, :holding_share)",id=session["user_id"], symbol=stock["symbol"], holding_share=share)
        else: # 若買過了,就找到該股票去增加持股
            db.execute("UPDATE porfolio SET holding_share = holding_share + :number WHERE id = :id AND symbol = :symbol", id=session["user_id"], symbol=stock["symbol"], number=share)

        return redirect(url_for("index"))

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    history = db.execute("SELECT * FROM history WHERE id = :id", id=session["user_id"])

    if not history:
        return apology("no history record")
    else:
        return render_template("history.html", history=history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", "You dumbass")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        # If str is a SELECT, then execute returns a list of zero or more dict objects, inside of which are keys and values representing a table’s fields and cells, respectively.

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["h_password"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"] # 因為execute會回傳一個array值,所以如果要取用execute回傳的值,要先指定array中的第一個項目[0],才能用

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    if request.method == "POST":
        rows = lookup(request.form.get("symbol"))
        if not rows:
            return apology("can't quote this stock!")
        else:
            return render_template("quote2.html", stock = rows)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "GET": # 若是藉由GET指令,就讓使用者來到register.html這個頁面
        return render_template("register.html")
    elif request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username")
        elif not request.form.get("password"):
            return apology("password!", "dumbass!")
        elif not request.form.get("c_password"):
            return apology("must confirm your password")
        elif request.form.get("password") != request.form.get("c_password"):
            return apology("password doesn't match with confirmation")

        primary_key = db.execute("INSERT INTO users (username, h_password) VALUES(:username, :h_password)",
                    username=request.form.get("username"), h_password=pwd_context.hash(request.form.get("password")))
        # If str is an INSERT, and the table into which data was inserted contains an autoincrementing PRIMARY KEY, then execute returns the value of the newly inserted row’s primary key.
        # 以這裡來看,primary_key就是你新創的使用者的id,看你目前創到第幾個,就是多少

        if primary_key == None: # 因為username已經被設定成Unique field Index,所以不能重複,若因為重複而創不成功,primary_key就會是None
            return apology("Username is already used")

        # 記住登入的使用者
        session["user_id"] = primary_key
        return redirect(url_for("index"))

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "GET":
        porfolio = db.execute("SELECT * FROM porfolio WHERE id = :id", id=session["user_id"])
        stock = [] # 為了要存porfolio裡買過的股票的資訊 [{'name':''}, {'symbol':''}, {'price': }]
        for i in range(0, len(porfolio)):
            stock.append(lookup(porfolio[i]["symbol"]))

        # 把stock list裡的dict新增進porfolio list的dict裡
        for i in range(0, len(porfolio)):
            porfolio[i]["name"] = stock[i]["name"]
            porfolio[i]["price"] = '%.2f' % stock[i]["price"]
            porfolio[i]["total"] = '%.2f' % (stock[i]["price"] * porfolio[0]["holding_share"])
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        porfolio[0]["cash"] = '%.2f' % cash[0]["cash"]
        return render_template("sell.html", porfolio=porfolio)

    elif request.method == "POST":
        if not request.form.get("stock_symbol"):
            return apology("invalid stock symbol")
        elif request.form.get("shares") == "" or int(request.form.get("shares")) <= 0:
            return apology("invalid shares")

        share = int(request.form.get("shares"))

        # 將使用者買過的該股票叫出來, 並檢查使用者有沒有購入這檔股票,或持有的數量夠不夠賣
        user_stocks = db.execute("SELECT holding_share FROM porfolio WHERE id = :id AND symbol = :symbol", id = session["user_id"], symbol = request.form.get("stock_symbol"))
        if not user_stocks:
            return apology("you don't have this stock!")
        elif user_stocks[0]["holding_share"] < share:
            return apology("you can't sell amount more than you have")

        # 取得這檔股票的現價
        stock = lookup(request.form.get("stock_symbol"))

        # 儲存賣賣紀錄
        utc_dt = datetime.utcnow() # 以utc時間型式儲存在資料庫裡
        db.execute("INSERT INTO history (id, symbol, stock_name, shares, price, total, datetime) VALUES (:id, :symbol, :stock_name, :shares, :price, :total, :datetime)",
                    id=session["user_id"], symbol=stock["symbol"], stock_name=stock["name"], shares= -share,
                    price=float(stock["price"]), total=share*float(stock["price"]), datetime=utc_dt)

        # 更新使用者的現金
        db.execute("UPDATE users SET cash = cash + :sales WHERE id = :id", id = session["user_id"], sales = share*float(stock["price"]))

        #更新使用者的持股數量
        db.execute("UPDATE porfolio SET holding_share = holding_share - :sales WHERE id = :id AND symbol = :symbol",
                    id=session["user_id"], symbol=stock["symbol"], sales=share)

        return redirect(url_for("index"))
