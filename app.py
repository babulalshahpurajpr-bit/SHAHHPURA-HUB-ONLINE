
import os, sqlite3, hashlib, secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key")
DB="shop.db"

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL, stock INTEGER, emoji TEXT, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, address TEXT, city TEXT, pin TEXT, payment TEXT, total REAL, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, qty INTEGER, price REAL);
    """)
    if c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]==0:
        products=[
        ("Premium Cotton T-Shirt","Fashion",499,20,"👕"),("Smart LED TV 43 inch","Electronics",24999,8,"📺"),
        ("Kitchen Storage Set","Home & Kitchen",799,15,"🍱"),("Daily Grocery Pack","Grocery",699,30,"🛒"),
        ("Running Shoes","Footwear",1299,12,"👟"),("Beauty Care Kit","Beauty",899,18,"💄"),
        ("Kids Building Blocks","Kids & Toys",599,14,"🧸"),("Bluetooth Earbuds","Electronics",999,25,"🎧")]
        c.executemany("INSERT INTO products(name,category,price,stock,emoji) VALUES(?,?,?,?,?)",products)
    c.commit(); c.close()

def pw(x): return hashlib.sha256(x.encode()).hexdigest()

@app.route("/")
def home():
    q=request.args.get("q","").strip()
    cat=request.args.get("cat","All")
    c=db()
    products=c.execute("SELECT * FROM products WHERE active=1 AND name LIKE ? AND (?='All' OR category=?) ORDER BY id DESC", (f"%{q}%",cat,cat)).fetchall()
    cats=c.execute("SELECT DISTINCT category FROM products WHERE active=1 ORDER BY category").fetchall()
    c.close()
    return render_template("home.html",products=products,cats=cats,q=q,cat=cat)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); phone=request.form["phone"].strip(); password=request.form["password"]
        if not name or not phone or len(password)<4: flash("Please enter valid details."); return redirect(url_for("register"))
        c=db()
        try:
            c.execute("INSERT INTO users(name,phone,password) VALUES(?,?,?)",(name,phone,pw(password))); c.commit()
            flash("Account created. Please login."); return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This mobile number is already registered.")
        finally: c.close()
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE phone=? AND password=?",(request.form["phone"].strip(),pw(request.form["password"]))).fetchone(); c.close()
        if u:
            session["uid"]=u["id"]; session["name"]=u["name"]; session["admin"]=u["is_admin"]; return redirect(url_for("home"))
        flash("Invalid mobile number or password.")
    return render_template("auth.html",mode="login")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

def get_cart():
    return session.get("cart",{})

@app.route("/cart")
def cart():
    cart=get_cart(); ids=list(map(int,cart.keys()))
    products=[]
    if ids:
        c=db(); products=c.execute(f"SELECT * FROM products WHERE id IN ({','.join('?'*len(ids))})",ids).fetchall(); c.close()
    total=sum(p["price"]*cart[str(p["id"])] for p in products)
    return render_template("cart.html",products=products,cart=cart,total=total)

@app.post("/cart/add/<int:pid>")
def add(pid):
    c=db(); p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(pid,)).fetchone(); c.close()
    if not p or p["stock"]<1: flash("Product unavailable."); return redirect(url_for("home"))
    cart=get_cart(); k=str(pid); cart[k]=min(cart.get(k,0)+1,p["stock"]); session["cart"]=cart
    return redirect(request.referrer or url_for("home"))

@app.post("/cart/change/<int:pid>")
def change(pid):
    cart=get_cart(); k=str(pid); n=int(request.form.get("qty",1))
    if n<=0: cart.pop(k,None)
    else: cart[k]=n
    session["cart"]=cart; return redirect(url_for("cart"))

@app.route("/checkout",methods=["GET","POST"])
def checkout():
    if not session.get("uid"): return redirect(url_for("login"))
    cart=get_cart()
    if not cart: return redirect(url_for("cart"))
    c=db(); ids=list(map(int,cart.keys()))
    products=c.execute(f"SELECT * FROM products WHERE id IN ({','.join('?'*len(ids))})",ids).fetchall()
    total=sum(p["price"]*cart[str(p["id"])] for p in products)
    if request.method=="POST":
        address=request.form["address"].strip(); city=request.form["city"].strip(); pin=request.form["pin"].strip(); payment=request.form["payment"]
        if not address or not city or not pin: flash("Delivery address is required."); c.close(); return redirect(url_for("checkout"))
        for p in products:
            if cart[str(p["id"])]>p["stock"]: flash(f"Insufficient stock: {p['name']}"); c.close(); return redirect(url_for("cart"))
        cur=c.execute("INSERT INTO orders(user_id,address,city,pin,payment,total,status) VALUES(?,?,?,?,?,?,?)",(session["uid"],address,city,pin,payment,total,"Order Received"))
        oid=cur.lastrowid
        for p in products:
            qty=cart[str(p["id"])]
            c.execute("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)",(oid,p["id"],qty,p["price"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,p["id"]))
        c.commit(); c.close(); session["cart"]={}; return redirect(url_for("orders"))
    c.close(); return render_template("checkout.html",products=products,cart=cart,total=total)

@app.route("/orders")
def orders():
    if not session.get("uid"): return redirect(url_for("login"))
    c=db(); orders=c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",(session["uid"],)).fetchall(); c.close()
    return render_template("orders.html",orders=orders)

@app.route("/admin",methods=["GET","POST"])
def admin():
    if not session.get("admin"): return redirect(url_for("login"))
    c=db()
    if request.method=="POST":
        name=request.form["name"]; category=request.form["category"]; price=float(request.form["price"]); stock=int(request.form["stock"]); emoji=request.form.get("emoji","📦")
        c.execute("INSERT INTO products(name,category,price,stock,emoji) VALUES(?,?,?,?,?)",(name,category,price,stock,emoji)); c.commit()
    products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders=c.execute("""SELECT o.*,u.name,u.phone FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC""").fetchall()
    c.close(); return render_template("admin.html",products=products,orders=orders)

@app.post("/admin/status/<int:oid>")
def admin_status(oid):
    if not session.get("admin"): return redirect(url_for("login"))
    c=db(); c.execute("UPDATE orders SET status=? WHERE id=?",(request.form["status"],oid)); c.commit(); c.close(); return redirect(url_for("admin"))

@app.post("/admin/seed-admin")
def seed_admin():
    if not session.get("admin"): return redirect(url_for("login"))
    return redirect(url_for("admin"))

if __name__=="__main__":
    init()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
