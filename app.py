from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask import jsonify
import MySQLdb.cursors
from datetime import datetime
from decimal import Decimal
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration (using XAMPP)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'bliciousseries'

mysql = MySQL(app)

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to create the database and tables
def create_database_and_tables():
    try:
        # Connect to MySQL
        connection = MySQLdb.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            passwd=app.config['MYSQL_PASSWORD']
        )
        cursor = connection.cursor()

        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS bliciousseries")
        connection.select_db(app.config['MYSQL_DB'])

        # Create users table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                mobile VARCHAR(20),
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                dob DATE,
                role VARCHAR(50) NOT NULL,
                referral_code VARCHAR(50) NULL
            )
        """)

        # Create products table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                retail_price DECIMAL(10, 2) NOT NULL,
                wholesale_price DECIMAL(10, 2) NOT NULL,
                commission DECIMAL(10, 2) NOT NULL,
                quantity INT NOT NULL,
                image VARCHAR(255) NULL
            )
        """)

        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                role VARCHAR(50),
                status ENUM('pending', 'proceed', 'decline', 'delivery', 'completed') DEFAULT 'pending',
                payment_status ENUM('pay_now', 'pay_later') DEFAULT 'pay_now',
                payment_verify_status ENUM('unpaid', 'paid', 'pending') DEFAULT NULL,
                referral_code_used VARCHAR(50),
                receipt_image VARCHAR(255),
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                cancelled_by VARCHAR(20) DEFAULT NULL,
                shipping_name VARCHAR(255),
                shipping_phone VARCHAR(20),
                shipping_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)



        # Create order_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                product_id INT,
                quantity INT NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)

        # Create sales table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                amount DECIMAL(10, 2),
                role VARCHAR(50),
                sale_month INT,
                sale_year INT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Create login_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                clerk_id INT,
                login_time DATETIME,
                logout_time DATETIME,
                FOREIGN KEY (clerk_id) REFERENCES users(id)
            )
        """)

        connection.commit()
        cursor.close()
        connection.close()
        print("Database and tables initialized successfully.")
    except Exception as e:
        print(f"Error creating database or tables: {e}")

# Function to insert owner data
def insert_owner_data():
    try:
        # Connect to the database
        connection = MySQLdb.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            passwd=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB']
        )
        cursor = connection.cursor()

        # Check if owner already exists
        cursor.execute("SELECT * FROM users WHERE role = 'owner'")
        owner_exists = cursor.fetchone()

        if not owner_exists:
            # Insert owner data with NULL referral code
            cursor.execute("""
                INSERT INTO users (name, mobile, email, password, dob, role, referral_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('Owner Name', '0123456789', 'owner@example.com', 'securepassword', '1980-01-01', 'owner', None))

            connection.commit()
            print("Owner data inserted successfully.")
        else:
            print("Owner data already exists. No insertion needed.")

        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error inserting owner data: {e}")




if __name__ == '__main__':
    # Create database and tables
    create_database_and_tables()
    # Insert owner data
    insert_owner_data()


# Main login page (redirects to /login)


# ------------------------------------------------------------------------------
# # AUTHENTICATION ROUTES
# ------------------------------------------------------------------------------
@app.route('/')
def login_page():
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Validation checks
        if '@' not in email:
            error_message = "Enter a valid email (name@email.com) <br> <a href='/forgot-password'>Forgot Password?</a>"
            return render_template('login.html', error_message=error_message)

        if len(password) < 6:
            error_message = "Password must be at least 6 characters long. <br> <a href='/forgot-password'>Forgot Password?</a>"
            return render_template('login.html', error_message=error_message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            session['role'] = user['role']
            session['email'] = email
            session['user_id'] = user['id']

            # ✅ Log login time if clerk
            if user['role'] == 'clerk':
                cursor.execute("""
                    INSERT INTO login_logs (clerk_id, login_time)
                    VALUES (%s, NOW())
                """, (user['id'],))
                mysql.connection.commit()
                session['log_id'] = cursor.lastrowid  # Store log_id in session

            cursor.close()

            # Redirect based on role
            if user['role'] == 'owner':
                return redirect(url_for('owner_dashboard'))
            elif user['role'] == 'clerk':
                return redirect(url_for('clerk_dashboard'))
            elif user['role'] == 'agent':
                return redirect(url_for('agent_dashboard'))
            elif user['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))
        else:
            cursor.close()
            error_message = "Incorrect email or password. <br> <a href='/forgot-password'>Forgot Password?</a>"
            return render_template('login.html', error_message=error_message)

    return render_template('login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        # Check if the new password meets the minimum length requirement
        if len(new_password) < 6:
            error_message = "Password must be at least 6 characters long."
            return render_template('forgot_password.html', error_message=error_message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
            mysql.connection.commit()
            cursor.close()
            success_message = "Password updated successfully."
            return render_template('forgot_password.html', success_message=success_message)
        else:
            cursor.close()
            error_message = "Email not found. Please try again."
            return render_template('forgot_password.html', error_message=error_message)

    return render_template('forgot_password.html')


# Dashboard routes


# ------------------------------------------------------------------------------
# # DASHBOARD ROUTES
# ------------------------------------------------------------------------------
@app.route('/owner/dashboard')
def owner_dashboard():
    if session.get('role') == 'owner':
        return render_template('owner/owner_dashboard.html')
    return "Access denied. Only owners can access this page.", 403

@app.route('/clerk/dashboard')
def clerk_dashboard():
    if session.get('role') == 'clerk':
        return render_template('clerk_dashboard.html')
    return "Access denied. Only clerks can access this page.", 403

@app.route('/agent/dashboard')
def agent_dashboard():
    if session.get('role') == 'agent':
        return render_template('agent_dashboard.html')
    return "Access denied. Only agents can access this page.", 403

@app.route('/customer/dashboard')
def customer_dashboard():
    if session.get('role') == 'customer':
        return render_template('customer_dashboard.html')
    return "Access denied. Only customers can access this page.", 403

# Registration routes
@app.route('/customer/register', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        dob = request.form['dob']
        password = request.form['password']

        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO users (name, mobile, email, dob, password, role) VALUES (%s, %s, %s, %s, %s, 'customer')", 
                           (name, mobile, email, dob, password))
            mysql.connection.commit()
            cursor.close()
            success_message = "Yeay! You have successfully registered! >_<"
            return render_template('register_customer.html', success_message=success_message)
        except Exception as e:
            print(f"Error: {e}")
            error_message = "Oh no. Failed to register. Please try again. T_T "
            return render_template('register_customer.html', error_message=error_message)
    return render_template('register_customer.html')

@app.route('/owner/register_clerk', methods=['GET', 'POST'])
def register_clerk():
    if session.get('role') != 'owner':
        return "Access denied. Only owners can register clerks.", 403

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        dob = request.form['dob']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            error_message = "Passwords do not match."
            return render_template('owner/register_clerk.html', error_message=error_message)
       
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO users (name, mobile, email, dob, password, role) VALUES (%s, %s, %s, %s, %s, 'clerk')", 
                           (name, mobile, email, dob, password))
            mysql.connection.commit()
            cursor.close()
            success_message = "Clerk registered successfully!"
            return render_template('owner/register_clerk.html', success_message=success_message)
        except Exception as e:
            print(f"Error: {e}")
            error_message = "Failed to register clerk. Please try again."
            return render_template('owner/register_clerk.html', error_message=error_message)
    return render_template('owner/register_clerk.html')

@app.route('/clerk/register_agent', methods=['GET', 'POST'])
def register_agent():
    if session.get('role') != 'clerk':
        return "Access denied. Only clerks can register agents.", 403

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        dob = request.form['dob']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            error_message = "Passwords do not match."
            return render_template('register_agent.html', error_message=error_message)

        try:
            # Get the current year and month
            now = datetime.now()
            year = now.strftime('%y')  # Get last two digits of the year
            month = now.strftime('%m')  # Get two-digit month

            # Count existing agents for the current year and month
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("""
                SELECT COUNT(*) AS agent_count
                FROM users
                WHERE role = 'agent' AND referral_code LIKE %s
            """, (f"{year}{month}%",))  # Count agents with referral codes matching year and month
            agent_count = cursor.fetchone()['agent_count']

            # Generate the referral code
            sequence = agent_count + 1
            referral_code = f"{year}{month}{sequence:02d}"  # Pad sequence with zeroes

            # Insert agent data with referral code
            cursor.execute("""
                INSERT INTO users (name, mobile, email, dob, password, role, referral_code)
                VALUES (%s, %s, %s, %s, %s, 'agent', %s)
            """, (name, mobile, email, dob, password, referral_code))

            mysql.connection.commit()
            cursor.close()

            success_message = "Agent registered successfully!"
            return render_template('register_agent.html', success_message=success_message)

        except Exception as e:
            print(f"Error: {e}")
            error_message = "Failed to register agent. Please try again."
            return render_template('register_agent.html', error_message=error_message)

    return render_template('register_agent.html')


# Route to view referral code
# from agent dashboard


# ------------------------------------------------------------------------------
# # REFERRAL CODE ROUTE
# ------------------------------------------------------------------------------
@app.route('/view_referral_code')
def view_referral_code():
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        
        # Query the database to get the referral code for the logged-in agent
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT referral_code FROM users WHERE id = %s AND role = 'agent'", (user_id,))
        agent = cursor.fetchone()

        # If the agent is found, render the referral code page
        if agent:
            return render_template('view_referral_code.html', referral_code=agent['referral_code'])
        else:
            return "Agent not found or you are not logged in as an agent.", 404
    else:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

#clerk dashboard to manage product
# Manage Products Page


# ------------------------------------------------------------------------------
# # PRODUCT MANAGEMENT
# ------------------------------------------------------------------------------
@app.route('/manage_products')
def manage_products():
    cursor = mysql.connection.cursor()
    # Execute the query to fetch all products
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    # Render the 'manage_products.html' template and pass the products data
    return render_template('manage_products.html', products=products)

# Add New Product Page
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        retail_price = Decimal(request.form['retail_price'])
        commission = Decimal(request.form['commission'])
        quantity = request.form['quantity']  # Change stock to quantity
        image = request.files['image']  # Change photo to image

        wholesale_price = retail_price - commission
        
        # Check if the product already exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM products WHERE name = %s", (name,))
        existing_product = cursor.fetchone()

        if existing_product:
            flash('Product with this name already exists!', 'danger')
            return render_template('add_product.html')

        image_filename = None
        if image and (image.filename.endswith('.jpg') or image.filename.endswith('.png')):
            image_filename = image.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)

        try:
            # Insert the new product into the database
            cursor.execute("""
                INSERT INTO products (name, description, retail_price, wholesale_price, commission, quantity, image)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, description, retail_price, wholesale_price, commission, quantity, image_filename))
            mysql.connection.commit()
            flash('The product is added successfully!', 'success')
        except Exception as e:
            flash('Failed to add new product. Please try again later.', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('add_product'))

    return render_template('add_product.html')


# Edit Product Page
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (id,))  # Use product_id as column
    product = cursor.fetchone()
    cursor.close()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        retail_price = Decimal(request.form['retail_price'])
        commission = Decimal(request.form['commission'])
        quantity = request.form['quantity']
        image = request.files['image']

        wholesale_price = retail_price - commission
        image_filename = product[7]  # Use the existing image filename as default
        
        if image and (image.filename.endswith('.jpg') or image.filename.endswith('.png')):
            image_filename = image.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE products
            SET name = %s, description = %s, retail_price = %s, wholesale_price = %s,
                commission = %s, quantity = %s, image = %s
            WHERE product_id = %s
        """, (name, description, retail_price, wholesale_price, commission, quantity, image_filename, id))
        mysql.connection.commit()
        cursor.close()

        flash('Product updated successfully!', 'success')
        return redirect(url_for('manage_products'))

    return render_template('edit_product.html', product=product)

# Delete Product
@app.route('/delete_product/<int:id>')
def delete_product(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM products WHERE product_id = %s", (id,))  # Use product_id in WHERE clause
    mysql.connection.commit()
    cursor.close()
    # Redirect to manage products page
    return redirect(url_for('manage_products'))

#View product
#Clerk
@app.route('/view_product/<int:id>')
def view_product(id):
    cursor = mysql.connection.cursor()
    # Fetch the product details using product_id
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (id,))
    product = cursor.fetchone()
    cursor.close()

    # If product is not found, show an error
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('manage_products'))

    # Render the view_product.html template and pass the product data
    return render_template('view_product.html', product=product)
#Customer
@app.route('/view_product_customer/<int:id>')
def view_product_customer(id):
    cursor = mysql.connection.cursor()
    # Fetch the product details using product_id
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (id,))
    product = cursor.fetchone()
    cursor.close()
    
    # Pass the product data to the template
    return render_template('view_product_customer.html', product=product)
#Agent
@app.route('/view_product_agent/<int:id>')
def view_product_agent(id):
    cursor = mysql.connection.cursor()
    # Fetch the product details using product_id
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (id,))
    product = cursor.fetchone()
    cursor.close()
    
    # Pass the product data to the template
    return render_template('view_product_agent.html', product=product)

#show list name
#clerk view agent list
@app.route('/clerk/agent_list', methods=['GET', 'POST'])
def agent_list():
    if session.get('role') != 'clerk':
        return "Access denied. Only clerk can view the agent list.", 403

    search = request.form.get('search', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search:
        cursor.execute("""
            SELECT * FROM users 
            WHERE role='agent' AND (name LIKE %s OR mobile LIKE %s OR email LIKE %s OR referral_code LIKE %s)
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM users WHERE role='agent'")

    users = cursor.fetchall()
    cursor.close()

    return render_template('agent_list.html', users=users, search=search)

#edit agent
@app.route('/clerk/edit_agent/<int:id>', methods=['GET', 'POST'])
def edit_agent(id):
    if session.get('role') != 'clerk':
        return "Access denied.", 403

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        dob = request.form['dob']
        referral_code = request.form['referral_code']

        cursor.execute("""
            UPDATE users SET name=%s, mobile=%s, email=%s, dob=%s, referral_code=%s
            WHERE id=%s AND role='agent'
        """, (name, mobile, email, dob, referral_code, id))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('agent_list'))

    cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'agent'", (id,))
    agent = cursor.fetchone()
    cursor.close()

    if not agent:
        return "Agent not found.", 404

    return render_template('edit_agent.html', agent=agent)

    
#delete agent
@app.route('/clerk/delete_agent/<int:id>', methods=['POST'])
def delete_agent(id):
    if session.get('role') != 'clerk':
        return "Access denied.", 403

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s AND role = 'agent'", (id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('agent_list'))


#owner view clerk list
@app.route('/owner/clerk_list', methods=['GET', 'POST'])
def clerk_list():
    if session.get('role') != 'owner':
        return "Access denied. Only owner can view the clerk list.", 403

    search = request.form.get('search', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search:
        cursor.execute("""
            SELECT * FROM users 
            WHERE role='clerk' AND (name LIKE %s OR mobile LIKE %s OR email LIKE %s)
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM users WHERE role='clerk'")

    users = cursor.fetchall()
    cursor.close()

    return render_template('owner/clerk_list.html', users=users, search=search)
#edit clerks
@app.route('/owner/edit_clerk/<int:id>', methods=['GET', 'POST'])
def edit_clerk(id):
    if session.get('role') != 'owner':
        return "Access denied.", 403

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        dob = request.form['dob']

        cursor.execute("""
            UPDATE users SET name=%s, mobile=%s, email=%s, dob=%s 
            WHERE id=%s AND role='clerk'
        """, (name, mobile, email, dob, id))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('clerk_list'))

    cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'clerk'", (id,))
    clerk = cursor.fetchone()
    cursor.close()

    if not clerk:
        return "Clerk not found.", 404

    return render_template('owner/edit_clerk.html', clerk=clerk)
#delete clerks
@app.route('/owner/delete_clerk/<int:id>', methods=['POST'])
def delete_clerk(id):
    if session.get('role') != 'owner':
        return "Access denied.", 403

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s AND role = 'clerk'", (id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('clerk_list'))


#view product for agent and customer


# ------------------------------------------------------------------------------
# # PRODUCT VIEW ROUTES
# ------------------------------------------------------------------------------
@app.route('/product_agent')
def product_agent():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    cursor.close()

    snacks = [p for p in all_products if p[1].lower() in [
        'popia udang', 'samosa ayam', 'kacang garlic', 'gajus salted egg'
    ]]
    cookies = [p for p in all_products if p not in snacks]

    return render_template('product_agent.html',
                           all_products=all_products,
                           snacks=snacks,
                           cookies=cookies)

@app.route('/product_customer')
def product_customer():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    cursor.close()

    snacks = [p for p in all_products if p[1].lower() in [
        'popia udang', 'samosa ayam', 'kacang garlic', 'gajus salted egg'
    ]]
    cookies = [p for p in all_products if p not in snacks]

    return render_template('product_customer.html',
                           all_products=all_products,
                           snacks=snacks,
                           cookies=cookies)


#--------------logout-------------
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    role = session.get('role')
    log_id = session.get('log_id')

    if role == 'clerk' and log_id:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE login_logs
            SET logout_time = NOW()
            WHERE log_id = %s AND clerk_id = %s
        """, (log_id, user_id))
        mysql.connection.commit()
        cursor.close()

    session.clear()
    return redirect(url_for('login'))



#---------------------------clerk manage order---------------------


# ------------------------------------------------------------------------------
# # ORDER MANAGEMENT
# ------------------------------------------------------------------------------
# ---------------------------------------------
# Clerk: Manage Orders
# ---------------------------------------------
@app.route('/clerk/manage_orders')
def clerk_manage_orders():
    if session.get('role') != 'clerk':
        return redirect(url_for('login'))

    filter_type = request.args.get('filter', 'all')
    per_page = int(request.args.get('per_page', 10))
    page = int(request.args.get('page', 1))
    offset = (page - 1) * per_page

    # ✅ User-provided date/month
    day_filter = request.args.get('date')
    month_filter = request.args.get('month')

    # ✅ Build status condition
    status_condition = ""
    if filter_type == 'active':
        status_condition = "AND o.status IN ('proceed', 'delivery')"
    elif filter_type == 'completed':
        status_condition = "AND o.status = 'completed'"
    elif filter_type == 'declined':
        status_condition = "AND o.status = 'decline'"
    elif filter_type == 'pending':
        status_condition = "AND o.status = 'pending'"

    # ✅ Only one filter: date OR month
    date_condition = ""
    params = []

    if day_filter:
        date_condition = " AND DATE(o.order_date) = %s"
        params.append(day_filter)
    elif month_filter:
        date_condition = " AND DATE_FORMAT(o.order_date, '%%Y-%%m') = %s"
        params.append(month_filter)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Apply params here!
    cursor.execute(f"""
        SELECT COUNT(*) as total
        FROM orders o
        WHERE 1=1 {status_condition} {date_condition}
    """, params)
    total_orders = cursor.fetchone()['total']
    has_next = total_orders > page * per_page

    cursor.execute(f"""
    SELECT o.order_id AS id,
           o.order_date,
           o.status,
           o.cancelled_by,
           o.receipt_image AS receipt,
           o.payment_status AS payment_method,
           u.name,
           u.role,  -- ✅ Add this line!
           SUM(oi.quantity * oi.unit_price) AS total
    FROM orders o
    JOIN users u ON o.user_id = u.id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE 1=1 {status_condition} {date_condition}
    GROUP BY o.order_id
    ORDER BY o.order_date DESC
    LIMIT %s OFFSET %s
""", params + [per_page, offset])


    orders = cursor.fetchall()

    start_entry = offset + 1
    end_entry = min(offset + per_page, total_orders)

    return render_template('clerk/clerk_manage_orders.html',
                           orders=orders,
                           page=page,
                           per_page=per_page,
                           total_orders=total_orders,
                           has_next=has_next,
                           start_entry=start_entry,
                           end_entry=end_entry,
                           active_tab=filter_type)


@app.route('/clerk/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if session.get('role') != 'clerk':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    new_status = request.form['new_status']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # If declining the order, restore product quantities
    if new_status == 'decline':
        cursor.execute("""
            SELECT product_id, quantity 
            FROM order_items 
            WHERE order_id = %s
        """, (order_id,))
        items = cursor.fetchall()
        for item in items:
            cursor.execute("""
                UPDATE products 
                SET quantity = quantity + %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))

        # Mark who cancelled
        cursor.execute("""
            UPDATE orders 
            SET status = %s, cancelled_by = 'clerk' 
            WHERE order_id = %s
        """, (new_status, order_id))
    else:
        # Regular update
        cursor.execute("""
            UPDATE orders 
            SET status = %s 
            WHERE order_id = %s
        """, (new_status, order_id))

    mysql.connection.commit()
    cursor.close()

    # ✅ Generate the new Action cell HTML so JS can replace it dynamically:
    if new_status == 'completed' or new_status == 'decline':
        new_action_html = f'<span class="btn-cancel">{new_status.title()}</span>'
    elif new_status == 'delivery':
        new_action_html = f'''
            <form method="POST" action="/clerk/update_order_status/{order_id}" class="update-status-form">
                <input type="hidden" name="new_status" value="completed">
                <button class="view-btn">🎉 Complete</button>
            </form>
        '''
    else:
        new_action_html = f'''
            <form method="POST" action="/clerk/update_order_status/{order_id}" class="update-status-form">
                <input type="hidden" name="new_status" value="delivery">
                <button class="view-btn">🚚 Delivery</button>
            </form>
        '''
    # ✅ Map new status to its next tab
    tab_map = {
        'proceed': 'active',   # pending → proceed → Active
        'delivery': 'active',  # proceed → delivery → stays in Active
        'completed': 'completed',  # delivery → completed → Completed
        'decline': 'declined'  # pending → decline → Declined
    }
    next_tab = tab_map.get(new_status, 'all')
   
    # ✅ Return JSON with the new HTML for the <td>
    return jsonify({
        'success': True,
        'order_id': order_id,
        'new_status': new_status,
        'new_action_html': new_action_html,
        'next_tab': next_tab
    })



@app.route('/clerk/order/<int:order_id>/details')
def clerk_order_details(order_id):
    if session.get('role') != 'clerk':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get order
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    if not order:
        return "Order not found", 404

    # Get items
    cursor.execute("""
        SELECT p.name, oi.unit_price, oi.quantity
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    order['total'] = sum(item['unit_price'] * item['quantity'] for item in items)

    cursor.close()
    return render_template('clerk/order_details_clerk.html', order=order, items=items)





# ---------------------------------------------
# Clerk: Manage Pay Later
# ---------------------------------------------
# ---------------------------------------------
# Clerk: Manage Pay Later (CLEAN FINAL)
# ---------------------------------------------
@app.route('/clerk/manage_paylater')
def clerk_manage_paylater():
    if session.get('role') != 'clerk':
        return redirect(url_for('login'))

    verify_filter = request.args.get('filter', 'all')

    if verify_filter == 'pending':
        # Pending: has receipt AND status is pending OR rejected
        verify_condition = """
            AND o.receipt_image IS NOT NULL
            AND o.payment_verify_status IN ('pending', 'unpaid')
        """
    elif verify_filter == 'unpaid':
        # Not Paid: NO receipt uploaded
        verify_condition = """
            AND o.receipt_image IS NULL
            AND (o.payment_verify_status IS NULL OR o.payment_verify_status = '' OR o.payment_verify_status = 'unpaid')
        """
    elif verify_filter in ['paid', 'complete']:
        # Complete: has receipt and approved
        verify_condition = """
            AND o.receipt_image IS NOT NULL
            AND o.payment_verify_status = 'paid'
        """
    else:
        # All: show everything grouped
        verify_condition = """
            AND (
                (o.receipt_image IS NOT NULL AND o.payment_verify_status IN ('pending', 'unpaid', 'paid'))
                OR (o.receipt_image IS NULL AND (o.payment_verify_status IS NULL OR o.payment_verify_status = '' OR o.payment_verify_status = 'unpaid'))
            )
        """

    # Date filters
    day_filter = request.args.get('date')
    month_filter = request.args.get('month')
    date_condition = ""
    params = []

    if day_filter:
        date_condition = " AND DATE(o.order_date) = %s"
        params.append(day_filter)
    elif month_filter:
        date_condition = " AND DATE_FORMAT(o.order_date, '%%Y-%%m') = %s"
        params.append(month_filter)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Count
    cursor.execute(f"""
        SELECT COUNT(DISTINCT o.order_id) AS total
        FROM orders o
        WHERE o.payment_status = 'pay_later'
          AND o.status = 'completed'
          {verify_condition}
          {date_condition}
    """, params)
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page

    # Fetch
    cursor.execute(f"""
        SELECT o.order_id, u.name, o.order_date AS receipt_uploaded_at,
               o.receipt_image, o.payment_verify_status,
               SUM(oi.quantity * oi.unit_price) AS total
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.payment_status = 'pay_later'
          AND o.status = 'completed'
          {verify_condition}
          {date_condition}
        GROUP BY o.order_id
        ORDER BY o.order_date DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    paylater_orders = cursor.fetchall()
    cursor.close()

    return render_template(
        'clerk/clerk_manage_paylater.html',
        paylater_orders=paylater_orders,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        active_tab=verify_filter
    )

# ---------------------------------------------
# Clerk: Update Pay Later Status
# ---------------------------------------------
@app.route('/clerk/update_paylater_status/<int:order_id>', methods=['POST'])
def update_paylater_status(order_id):
    if session.get('role') != 'clerk':
        return redirect(url_for('login'))

    new_status = request.form['new_status']  # 'paid' or 'unpaid'

    # Update in DB
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE orders SET payment_verify_status = %s WHERE order_id = %s",
        (new_status, order_id)
    )
    mysql.connection.commit()
    cursor.close()

    # Decide next tab:
    if new_status == 'paid':
        next_tab = 'paid'  # means "Complete"
    else:
        next_tab = 'pending'  # stay in Pending if rejected

    flash(f"Pay later order #{order_id} updated to {new_status.title()}.", 'success')
    return redirect(url_for('clerk_manage_paylater', filter=next_tab))


#------------------------------customer cart, pay and order status------------------------------
import os, json
from werkzeug.utils import secure_filename


# ------------------------------------------------------------------------------
# # CUSTOMER MODULE
# ------------------------------------------------------------------------------
@app.route('/customer/cart')
def customer_cart():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
    return render_template("customer/cart_customer.html")


@app.route('/customer/checkout', methods=['POST'])
def customer_checkout():
    if session.get('role') != 'customer':
        return jsonify({"message": "Unauthorized"}), 403

    cart_data = request.form.get("cart")
    payment_status = request.form.get("payment_status")
    referral_code_input = request.form.get("referral_code")
    receipt_file = request.files.get("receipt")
    shipping_name = request.form.get("shipping_name")
    shipping_phone = request.form.get("shipping_phone")
    shipping_address = request.form.get("shipping_address")

    if not cart_data:
        return jsonify({"message": "Cart is empty."}), 400

    try:
        cart_items = json.loads(cart_data)
    except Exception:
        return jsonify({"message": "Invalid cart format."}), 400

    filename = None
    if receipt_file and receipt_file.filename:
        ext = os.path.splitext(receipt_file.filename)[1]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"receipt_{timestamp}{ext}"
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        receipt_file.save(receipt_path)

    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Validate referral code
    referred_agent = None
    if referral_code_input:
        referral_code_input = referral_code_input.strip()
        cursor.execute(
            "SELECT id FROM users WHERE referral_code = %s AND role = 'agent'", 
            (referral_code_input,)
        )
        referred_agent = cursor.fetchone()
        if not referred_agent:
            return jsonify({"message": "Invalid referral code. Please try again."}), 400

    # ✅ STOCK VALIDATION: check each product
    for item in cart_items:
        cursor.execute(
        "SELECT name, quantity FROM products WHERE product_id = %s",
        (item["id"],)
    )
    product = cursor.fetchone()
    if not product:
        return jsonify({"message": "Product not found."}), 400

    if int(item["quantity"]) > int(product["quantity"]):
        return jsonify({
            "message": f"Not enough stock for '{product['name']}'. "
                       f"Only {product['quantity']} left."
        }), 400


    # ✅ All valid → Insert order
    cursor.execute("""
        INSERT INTO orders (user_id, role, payment_status, referral_code_used, receipt_image,
                            shipping_name, shipping_phone, shipping_address)
        VALUES (%s, 'customer', %s, %s, %s, %s, %s, %s)
    """, (
        user_id, payment_status,
        referral_code_input if referred_agent else None,
        filename, shipping_name, shipping_phone, shipping_address
    ))
    mysql.connection.commit()
    order_id = cursor.lastrowid

    # ✅ Insert order items & reduce stock
    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
        """, (
            order_id, item["id"], item["quantity"], item["price"]
        ))

        cursor.execute("""
            UPDATE products 
            SET quantity = quantity - %s 
            WHERE product_id = %s
        """, (
            item["quantity"], item["id"]
        ))

    # ✅ Add RM1 commission if referral valid
    if referred_agent:
        agent_id = referred_agent['id']
        now = datetime.now()
        cursor.execute("""
            INSERT INTO sales (user_id, amount, role, sale_month, sale_year)
            VALUES (%s, 1.00, 'agent', %s, %s)
            ON DUPLICATE KEY UPDATE amount = amount + 1.00
        """, (
            agent_id, now.month, now.year
        ))

    mysql.connection.commit()
    cursor.close()

    return jsonify({"message": "Order placed successfully!"})







#---------------------customer order----------------------

@app.route('/customer/order')
def customer_orders():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page
    filter_type = request.args.get('filter', 'all')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Build filter condition
    status_condition = ""
    if filter_type == 'active':
        status_condition = "AND o.status IN ('pending', 'proceed', 'delivery')"
    elif filter_type == 'completed':
        status_condition = "AND o.status = 'completed'"
    elif filter_type == 'declined':
        status_condition = "AND o.status = 'decline'"

    # Get total count for pagination
    cursor.execute(f"""
        SELECT COUNT(*) as total FROM orders o
        WHERE o.user_id = %s {status_condition}
    """, (user_id,))
    total_orders = cursor.fetchone()['total']
    has_next = total_orders > page * per_page

    # Fetch paginated orders
    cursor.execute(f"""
        SELECT o.*, 
               (SELECT SUM(oi.quantity * oi.unit_price) FROM order_items oi WHERE oi.order_id = o.order_id) AS total
        FROM orders o
        WHERE o.user_id = %s {status_condition}
        ORDER BY o.order_date DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))

    orders = cursor.fetchall()
    cursor.close()

    start_entry = offset + 1
    end_entry = min(offset + per_page, total_orders)

    return render_template("customer/order_customer.html",
                           orders=orders,
                           page=page,
                           per_page=per_page,
                           total_orders=total_orders,
                           has_next=has_next,
                           start_entry=start_entry,
                           end_entry=end_entry,
                           active_tab=filter_type)


@app.route('/customer/order/<int:order_id>/details')
def order_customer_details(order_id):
    if session.get('role') != 'customer':
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch order info
    cursor.execute("SELECT * FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    if not order:
        return "Order not found", 404

    # Fetch ordered items
    cursor.execute("""
        SELECT p.name, oi.unit_price, oi.quantity
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    order['total'] = sum(item['unit_price'] * item['quantity'] for item in items)
    cursor.close()

    return render_template('customer/order_customer_details.html', order=order, items=items)


@app.route('/customer/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order_customer(order_id):
    if session.get('role') != 'customer':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # First, check if the order can be cancelled (must be pending and owned by this user)
    cursor.execute("""
        SELECT status FROM orders 
        WHERE order_id = %s AND user_id = %s AND status = 'pending'
    """, (order_id, user_id))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        flash("Order cannot be cancelled.", "danger")
        return redirect(url_for('customer_orders'))

    # Mark the order as cancelled
    cursor.execute("""
        UPDATE orders 
        SET status = 'decline', cancelled_by = 'customer'
        WHERE order_id = %s
    """, (order_id,))

    # Restore quantities of the products
    cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
    items = cursor.fetchall()
    for item in items:
        cursor.execute("""
            UPDATE products 
            SET quantity = quantity + %s 
            WHERE product_id = %s
        """, (item['quantity'], item['product_id']))

    mysql.connection.commit()
    cursor.close()

    flash("Your order has been cancelled successfully!", "success")
    return redirect(url_for('customer_orders'))




# ------------------------------------------------------------------------------
# # SALES MODULE
# ------------------------------------------------------------------------------
@app.route('/clerk/sales_clerk', methods=['GET', 'POST'])
def sales_clerk():
    import io
    import csv
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    view_type = request.form.get('view_type', 'order')
    filter_type = request.form.get('filter_type', 'all')
    search_query = request.form.get('search_query', '')
    selected_month = int(request.form.get('month', datetime.now().month))
    selected_year = int(request.form.get('year', datetime.now().year))
    export = request.form.get('export_excel')

    chart_labels = []
    chart_data = []
    chart_quantity = []
    pie_labels = []
    pie_data = []
    line_labels = []
    line_data = []
    total_quantity = 0
    total_amount = 0.0

    if view_type == 'order':
        # WHERE clause and parameters
        where_clause = "WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'"
        params = [selected_month, selected_year]

        if filter_type == 'agent':
            where_clause += " AND u.role = 'agent'"
            if search_query:
                where_clause += " AND (u.name LIKE %s OR u.referral_code LIKE %s)"
                params.extend([f"%{search_query}%", f"%{search_query}%"])
        elif filter_type == 'customer':
            where_clause += " AND u.role = 'customer'"

        # Total quantity and amount
        cursor.execute(f"""
            SELECT SUM(oi.quantity) AS total_quantity, SUM(oi.quantity * oi.unit_price) AS total_amount
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN users u ON o.user_id = u.id
            {where_clause}
        """, tuple(params))
        result = cursor.fetchone()
        total_quantity = result['total_quantity'] or 0
        total_amount = float(result['total_amount']) if result['total_amount'] else 0.0

        # Pie chart for role-based sales
        if filter_type == 'all':
            cursor.execute("""
                SELECT u.role, SUM(oi.quantity * oi.unit_price) AS total
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN users u ON o.user_id = u.id
                WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
                GROUP BY u.role
            """, (selected_month, selected_year))
            roles = cursor.fetchall()
            for r in roles:
                pie_labels.append(r['role'])
                pie_data.append(float(r['total']))

        # Line chart for sales over days of the month
        cursor.execute(f"""
            SELECT DAY(o.order_date) AS day, SUM(oi.quantity * oi.unit_price) AS total
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN users u ON o.user_id = u.id
            {where_clause}
            GROUP BY day
            ORDER BY day
        """, tuple(params))
        line_results = cursor.fetchall()
        line_labels = [str(r['day']) for r in line_results]
        line_data = [float(r['total']) for r in line_results]

    elif view_type == 'product':
        cursor.execute("""
            SELECT p.name AS name, SUM(oi.quantity) AS total_quantity, SUM(oi.quantity * oi.unit_price) AS total
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN users u ON o.user_id = u.id
            WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
            GROUP BY p.name
            ORDER BY total_quantity DESC
        """, (selected_month, selected_year))
        product_results = cursor.fetchall()

        for row in product_results:
            chart_labels.append(row['name'])
            chart_quantity.append(int(row['total_quantity']))
            chart_data.append(float(row['total']))
            total_quantity += row['total_quantity'] or 0
            total_amount += float(row['total']) if row['total'] else 0.0

        if export:
            si = io.StringIO()
            cw = csv.writer(si)
            cw.writerow(['Product Name', 'Quantity', 'Total (RM)'])
            for row in product_results:
                cw.writerow([row['name'], row['total_quantity'], f"{row['total']:.2f}"])
            output = io.BytesIO()
            output.write(si.getvalue().encode('utf-8'))
            output.seek(0)
            return send_file(output,
                             mimetype='text/csv',
                             download_name=f'sales_product_report_{selected_month}_{selected_year}.csv',
                             as_attachment=True)

    return render_template("sales_clerk.html",
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           chart_quantity=chart_quantity,
                           total_quantity=total_quantity,
                           total_amount=total_amount,
                           pie_labels=pie_labels,
                           pie_data=pie_data,
                           line_labels=line_labels,
                           line_data=line_data,
                           filter_type=filter_type,
                           search_query=search_query,
                           selected_month=selected_month,
                           selected_year=selected_year,
                           view_type=view_type)







# ---------------- CART AND CHECKOUT ----------------

from flask import request, jsonify, render_template, redirect, url_for, session
import json, os
from datetime import datetime



# ------------------------------------------------------------------------------
# # AGENT MODULE
# ------------------------------------------------------------------------------
@app.route('/agent/cart')
def cart_agent():
    if session.get('role') != 'agent':
        return redirect(url_for('login'))
    return render_template('agent/cart_agent.html')  # ✅ use your updated HTML filename

@app.route('/agent/checkout', methods=['POST'])
def agent_checkout():
    if session.get('role') != 'agent':
        return jsonify({'message': 'Unauthorized'}), 403

    cart = json.loads(request.form.get('cart', '[]'))
    payment_status = request.form.get('payment_status', 'pay_now')
    receipt_file = request.files.get('receipt')
    shipping_name = request.form.get('shipping_name', '').strip()
    shipping_phone = request.form.get('shipping_phone', '').strip()
    shipping_address = request.form.get('shipping_address', '').strip()
    user_id = session.get('user_id')

    if not shipping_name or not shipping_phone or not shipping_address:
        return jsonify({'message': 'Shipping information is required.'}), 400

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        filename = None

        # Save receipt if paying now
        if payment_status == 'pay_now' and receipt_file and receipt_file.filename:
            ext = os.path.splitext(receipt_file.filename)[1]
            filename = f"receipt_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            receipt_file.save(filepath)

        # ✅ Validate stock for each product
        for item in cart:
            cursor.execute(
                "SELECT name, quantity FROM products WHERE product_id = %s",
                (item['id'],)
            )
            product = cursor.fetchone()
            if not product:
                return jsonify({'message': 'Product not found.'}), 400

            if int(item['quantity']) > int(product['quantity']):
                return jsonify({
                    'message': f"Not enough stock for '{product['name']}'. "
                               f"Only {product['quantity']} left."
                }), 400

        # ✅ All stock OK — insert order
        cursor.execute("""
            INSERT INTO orders (
                user_id, role, payment_status, status, receipt_image,
                shipping_name, shipping_phone, shipping_address
            )
            VALUES (%s, 'agent', %s, 'pending', %s, %s, %s, %s)
        """, (
            user_id, payment_status, filename,
            shipping_name, shipping_phone, shipping_address
        ))
        mysql.connection.commit()
        order_id = cursor.lastrowid

        # ✅ Insert order items & update stock
        for item in cart:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['id'], item['quantity'], item['price']))

            cursor.execute("""
                UPDATE products SET quantity = quantity - %s
                WHERE product_id = %s
            """, (item['quantity'], item['id']))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Order placed successfully!'})

    except Exception as e:
        print("Checkout error:", e)
        return jsonify({'message': 'Failed to place order'}), 500


#--------------------agent order page---------------------------
@app.route('/agent/order')
def order_agent():
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session['user_id']
    filter_type = request.args.get('filter', 'all')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if filter_type == 'active':
        status_condition = "AND status IN ('pending', 'proceed', 'delivery')"
    elif filter_type == 'completed':
        status_condition = "AND status = 'completed'"
    elif filter_type == 'declined':
        status_condition = "AND status IN ('decline', 'cancel')"
    else:
        status_condition = ""

    cursor.execute(f"""
        SELECT * FROM orders
        WHERE user_id = %s AND role = 'agent' {status_condition}
        ORDER BY order_date DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    orders = cursor.fetchall()

    enriched_orders = []

    for order in orders:
        cursor.execute("""
            SELECT SUM(quantity * unit_price) AS total
            FROM order_items
            WHERE order_id = %s
        """, (order['order_id'],))
        result = cursor.fetchone()
        total = result['total'] if result and result['total'] else 0.00

        # Format status nicely
        if order['status'] == 'decline':
            if order['cancelled_by'] == 'clerk':
                display_status = 'Declined'
            else:
                display_status = 'Cancelled'
        elif order['status'] == 'proceed':
            display_status = 'Proceed'
        elif order['status'] == 'delivery':
            display_status = 'Delivery'
        elif order['status'] == 'completed':
            display_status = 'Completed'
        else:
            display_status = 'Pending'

        # Add enriched order
        enriched_orders.append({
            **order,
            'total': total,
            'display_status': display_status
        })

    # Total count for pagination
    cursor.execute(f"""
        SELECT COUNT(*) as total FROM orders
        WHERE user_id = %s AND role = 'agent' {status_condition}
    """, (user_id,))
    total_orders = cursor.fetchone()['total']
    has_next = total_orders > page * per_page

    start_entry = offset + 1
    end_entry = min(offset + per_page, total_orders)

    return render_template(
        'agent/order_agent.html',
        orders=enriched_orders,
        active_tab=filter_type,
        page=page,
        per_page=per_page,
        total_orders=total_orders,
        has_next=has_next,
        start_entry=start_entry,
        end_entry=end_entry
    )



@app.route('/agent/order/<int:order_id>/details')
def order_agent_details(order_id):
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Order Info
    cursor.execute("SELECT * FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()

    if not order:
        return "Order not found", 404

    # Product Info (include unit_price)
    cursor.execute("""
        SELECT p.name, oi.unit_price, oi.quantity
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()  # KEEP THIS ONE

    # Calculate total
    total_price = sum(item['unit_price'] * item['quantity'] for item in items)
    order['total'] = total_price

    # DO NOT re-fetch items here again — it will clear the result
    # items = cursor.fetchall()  ← REMOVE THIS LINE

    return render_template('agent/order_agent_details.html', order=order, items=items)

@app.route('/agent/order/<int:order_id>/receipt')
def view_receipt(order_id):
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT receipt_image FROM orders WHERE order_id = %s AND user_id = %s", (order_id, session['user_id']))
    order = cursor.fetchone()

    if not order:
        return "Order not found", 404

    if not order['receipt_image']:
        return "<h3 style='text-align:center; font-family:Arial; margin-top: 50px;'>No receipt uploaded for this order.</h3>"

    return redirect(url_for('static', filename='uploads/' + order['receipt_image']))




@app.route('/agent/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Confirm the order is pending and belongs to the agent
    cursor.execute("""
        SELECT status FROM orders 
        WHERE order_id = %s AND user_id = %s AND status = 'pending'
    """, (order_id, user_id))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        flash("Order cannot be cancelled.", "danger")
        return redirect(url_for('order_agent'))

    # Update order to decline and track who cancelled
    cursor.execute("""
        UPDATE orders 
        SET status = 'decline', cancelled_by = 'agent' 
        WHERE order_id = %s
    """, (order_id,))

    # Restore product quantity
    cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
    items = cursor.fetchall()
    for item in items:
        cursor.execute("""
            UPDATE products 
            SET quantity = quantity + %s 
            WHERE product_id = %s
        """, (item['quantity'], item['product_id']))

    mysql.connection.commit()
    cursor.close()

    flash("Order cancelled successfully!", "success")
    return redirect(url_for('order_agent'))


#------------------sale agent-------------
@app.route('/sales_agent')
def sales_agent_page():
    if 'user_id' not in session or session.get('role') != 'agent':
        return redirect(url_for('login'))

    now = datetime.now()
    return render_template('sale_agent.html', current_month=now.month, current_year=now.year)

@app.route('/agent_sales_data')
def agent_sales_data():
    if 'user_id' not in session or session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session['user_id']
    view_type = request.args.get('view', 'own')
    year = int(request.args.get('year', datetime.now().year))
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    all_data = []

    # Own purchases
    if view_type in ['own', 'combined']:
        cursor.execute("""
            SELECT o.order_id, o.order_date, 'own' AS type,
                   ROUND(SUM(oi.quantity * p.commission), 2) AS commission
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.user_id = %s AND o.status = 'completed' AND YEAR(o.order_date) = %s
            GROUP BY o.order_id
        """, (user_id, year))
        all_data += cursor.fetchall()

    # Referral purchases
    if view_type in ['referral', 'combined']:
        cursor.execute("SELECT referral_code FROM users WHERE id = %s", (user_id,))
        code = cursor.fetchone()['referral_code']
        if code:
            cursor.execute("""
                SELECT order_id, order_date, 'referral' AS type,
                       1.00 AS commission
                FROM orders
                WHERE referral_code_used = %s AND status = 'completed' AND YEAR(order_date) = %s
            """, (code, year))
            all_data += cursor.fetchall()

    # Sort and paginate
    all_data.sort(key=lambda x: x['order_date'], reverse=True)
    total = len(all_data)
    paginated = all_data[offset:offset+per_page]
    for i, row in enumerate(paginated):
        row['no'] = offset + i + 1
        row['order_date'] = row['order_date'].strftime('%Y-%m-%d %H:%M:%S')
        row['commission'] = float(row['commission'])

    return jsonify({
        'orders': paginated,
        'total_sales': round(sum(row['commission'] for row in all_data), 2),
        'page': page,
        'per_page': per_page,
        'total_orders': total
    })

@app.route('/agent_sales_chart')
def agent_sales_chart():
    if 'user_id' not in session or session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session['user_id']
    year = int(request.args.get('year'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get agent's referral code
    cursor.execute("SELECT referral_code FROM users WHERE id = %s", (user_id,))
    referral_code = cursor.fetchone()['referral_code']

    own_monthly = [0] * 12
    ref_monthly = [0] * 12

    # OWN
    cursor.execute("""
    SELECT MONTH(o.order_date) AS month, 
           ROUND(SUM(oi.quantity * p.commission), 2) AS total
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.user_id = %s AND o.status = 'completed' AND YEAR(o.order_date) = %s
    GROUP BY MONTH(o.order_date)
""", (user_id, year))


    for row in cursor.fetchall():
        own_monthly[row['month'] - 1] = float(row['total'])

    # REFERRAL
    cursor.execute("""
        SELECT MONTH(order_date) AS month, COUNT(*) AS count
        FROM orders
        WHERE referral_code_used = %s AND status = 'completed' AND YEAR(order_date) = %s
        GROUP BY MONTH(order_date)
    """, (referral_code, year))
    for row in cursor.fetchall():
        ref_monthly[row['month'] - 1] = row['count'] * 1.00

    combined = [own_monthly[i] + ref_monthly[i] for i in range(12)]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    return jsonify({
        'months': months,
        'own': own_monthly,
        'referral': ref_monthly,
        'combined': combined
    })

#------------------------------ agent pay later ----------------------
@app.route('/agent/pay_later')
def pay_later():
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Include all pay_later orders that are NOT declined or cancelled
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.status, o.payment_status, o.receipt_image,
               o.payment_verify_status,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s 
          AND o.payment_status = 'pay_later'
          AND o.status NOT IN ('decline', 'cancel')
        GROUP BY o.order_id
        ORDER BY o.order_date DESC
    """, (user_id,))

    orders = cursor.fetchall()
    cursor.close()

    return render_template('agent/pay_later.html', orders=orders)

@app.route('/agent/pay_later/pay/<int:order_id>')
def pay_later_payment(order_id):
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    # Optionally verify the order belongs to the current agent and is unpaid
    user_id = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM orders 
        WHERE order_id = %s AND user_id = %s AND payment_status = 'pay_later'
    """, (order_id, user_id))
    order = cursor.fetchone()
    cursor.close()

    if not order:
        flash("Order not found or access denied.", "danger")
        return redirect(url_for('pay_later'))

    return render_template('agent/pay_later_payment.html', order_id=order_id)


@app.route('/agent/pay_later/submit/<int:order_id>', methods=['POST'])
def pay_later_submit(order_id):
    if session.get('role') != 'agent':
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    if 'receipt' not in request.files or request.files['receipt'].filename == '':
        flash('No file uploaded.', 'danger')
        return redirect(url_for('pay_later_payment', order_id=order_id))

    receipt_file = request.files['receipt']
    ext = os.path.splitext(receipt_file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
        flash('Invalid file type. Only images or PDFs allowed.', 'danger')
        return redirect(url_for('pay_later_payment', order_id=order_id))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"receipt_paylater_{order_id}_{timestamp}{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    receipt_file.save(filepath)

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE orders
        SET receipt_image = %s, payment_verify_status = 'pending'
        WHERE order_id = %s AND user_id = %s
    """, (filename, order_id, user_id))
    mysql.connection.commit()
    cursor.close()

    flash('Receipt uploaded successfully. Waiting for clerk verification.', 'success')
    return redirect(url_for('pay_later'))





#-----------------------------report owner-----------------
from datetime import datetime 
@app.route('/owner/report')
def owner_report():
    if session.get('role') != 'owner':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    month = request.args.get('month', default=datetime.now().month, type=int)
    year = request.args.get('year', default=datetime.now().year, type=int)

    # 1. Sales Summary
    cursor.execute("""
        SELECT SUM(oi.quantity * oi.unit_price) AS total_sales, 
               SUM(oi.quantity) AS total_quantity
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
    """, (month, year))
    summary = cursor.fetchone()

    # 2. Sales by Role (Pie Chart)
    cursor.execute("""
        SELECT u.role, SUM(oi.quantity * oi.unit_price) AS total
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN users u ON o.user_id = u.id
        WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
        GROUP BY u.role
    """, (month, year))
    role_sales = cursor.fetchall()

    # 3. Daily Sales (Line Chart)
    cursor.execute("""
        SELECT DAY(o.order_date) AS day, 
               SUM(oi.quantity * oi.unit_price) AS total
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
        GROUP BY day ORDER BY day
    """, (month, year))
    daily_sales = cursor.fetchall()

    # 4. Top Agents
    cursor.execute("""
        SELECT u.name, u.referral_code,
               SUM(oi.quantity * oi.unit_price) AS total_sales,
               COUNT(DISTINCT o.order_id) AS total_orders
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN users u ON o.user_id = u.id
        WHERE u.role = 'agent' AND MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
        GROUP BY u.id ORDER BY total_sales DESC
    """, (month, year))
    top_agents = cursor.fetchall()

    # 5. Clerk Login Logs (unchanged – not related to orders)
    cursor.execute("""
        SELECT u.name, l.login_time, l.logout_time
        FROM login_logs l
        JOIN users u ON l.clerk_id = u.id
        WHERE u.role = 'clerk' AND MONTH(l.login_time) = %s AND YEAR(l.login_time) = %s
        ORDER BY l.login_time DESC
    """, (month, year))
    login_logs = cursor.fetchall()

    # 6. Best-Selling Products
    cursor.execute("""
        SELECT p.name AS product_name,
               SUM(oi.quantity) AS total_quantity,
               SUM(oi.quantity * oi.unit_price) AS total_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE MONTH(o.order_date) = %s AND YEAR(o.order_date) = %s AND o.status = 'completed'
        GROUP BY p.product_id
        ORDER BY total_quantity DESC
    """, (month, year))
    all_products = cursor.fetchall()
    top5_products = all_products[:5]

    cursor.close()

    return render_template("owner/report_owner.html",
                           summary=summary,
                           role_sales=role_sales,
                           daily_sales=daily_sales,
                           top_agents=top_agents,
                           login_logs=login_logs,
                           top5_products=top5_products,
                           all_products=all_products,
                           month=month,
                           year=year,
                           datetime=datetime)

from flask import send_file
import io
import csv

@app.route('/owner/export_login_logs')
def export_login_logs():
    if session.get('role') != 'owner':
        return redirect(url_for('login'))

    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT u.name, l.login_time, l.logout_time
        FROM login_logs l
        JOIN users u ON l.clerk_id = u.id
        WHERE u.role = 'clerk' AND MONTH(l.login_time) = %s AND YEAR(l.login_time) = %s
        ORDER BY l.login_time DESC
    """, (month, year))
    logs = cursor.fetchall()
    cursor.close()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Clerk Name', 'Login Time', 'Logout Time'])
    for row in logs:
        writer.writerow([row['name'], row['login_time'], row['logout_time'] or ''])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'clerk_login_logs_{month}_{year}.csv'
    )




if __name__ == '__main__':
    app.run(debug=True)