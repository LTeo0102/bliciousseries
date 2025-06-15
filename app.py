from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ✅ Render PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------
# ✅ MODELS
# -------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date)
    role = db.Column(db.String(50))
    referral_code = db.Column(db.String(50))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    retail_price = db.Column(db.Numeric(10, 2))
    wholesale_price = db.Column(db.Numeric(10, 2))
    commission = db.Column(db.Numeric(10, 2))
    quantity = db.Column(db.Integer)
    image = db.Column(db.String(255))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')
    payment_status = db.Column(db.String(50))
    payment_verify_status = db.Column(db.String(50))
    referral_code_used = db.Column(db.String(50))
    receipt_image = db.Column(db.String(255))
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_by = db.Column(db.String(20))
    shipping_name = db.Column(db.String(255))
    shipping_phone = db.Column(db.String(20))
    shipping_address = db.Column(db.Text)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Numeric(10, 2))

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Numeric(10, 2))
    role = db.Column(db.String(50))
    sale_month = db.Column(db.Integer)
    sale_year = db.Column(db.Integer)

# -------------------------------
# ✅ ROUTES
# -------------------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/customer/register', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        new_user = User(
            name=request.form['name'],
            mobile=request.form['mobile'],
            email=request.form['email'],
            password=request.form['password'],
            dob=datetime.strptime(request.form['dob'], '%Y-%m-%d'),
            role='customer'
        )
        db.session.add(new_user)
        db.session.commit()
        return render_template('register_customer.html', success_message="Registered successfully!")
    return render_template('register_customer.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form['email']).first()
        if u and u.password == request.form['password']:
            session['role'] = u.role
            session['user_id'] = u.id
            return redirect(url_for(f"{u.role}_dashboard"))
        else:
            return render_template('login.html', error_message="Invalid credentials")
    return render_template('login.html')

@app.route('/owner/dashboard')
def owner_dashboard():
    return "Owner Dashboard" if session.get('role') == 'owner' else "Access Denied"

@app.route('/clerk/dashboard')
def clerk_dashboard():
    return "Clerk Dashboard" if session.get('role') == 'clerk' else "Access Denied"

@app.route('/agent/dashboard')
def agent_dashboard():
    return "Agent Dashboard" if session.get('role') == 'agent' else "Access Denied"

@app.route('/customer/dashboard')
def customer_dashboard():
    return "Customer Dashboard" if session.get('role') == 'customer' else "Access Denied"

# -------------------------------
# ✅ CRUD PRODUCTS
# -------------------------------
@app.route('/products')
def products():
    items = Product.query.all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'price': float(p.retail_price), 'stock': p.quantity
    } for p in items])

@app.route('/add_product', methods=['POST'])
def add_product():
    p = Product(
        name=request.form['name'],
        description=request.form['description'],
        retail_price=request.form['retail_price'],
        wholesale_price=request.form['wholesale_price'],
        commission=request.form['commission'],
        quantity=request.form['quantity'],
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'message': 'Product added'})

# -------------------------------
# ✅ CHECKOUT
# -------------------------------
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart = data['cart']
    new_order = Order(
        user_id=session.get('user_id'),
        role=session.get('role'),
        payment_status='pay_now',
        shipping_name=data['shipping_name'],
        shipping_phone=data['shipping_phone'],
        shipping_address=data['shipping_address'],
    )
    db.session.add(new_order)
    db.session.flush()

    for item in cart:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['product_id'],
            quantity=item['quantity'],
            unit_price=item['price']
        )
        p = Product.query.get(item['product_id'])
        p.quantity -= item['quantity']
        db.session.add(order_item)

    db.session.commit()
    return jsonify({'message': 'Order placed successfully'})

# -------------------------------
# ✅ REPORT (OWNER)
# -------------------------------
@app.route('/owner/report')
def owner_report():
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)
    sales = db.session.query(OrderItem).join(Order).filter(
        db.extract('month', Order.order_date) == month,
        db.extract('year', Order.order_date) == year
    ).all()
    total_sales = sum(i.quantity * i.unit_price for i in sales)
    return jsonify(total_sales=float(total_sales))

# -------------------------------
# ✅ DB INIT + MAIN
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
