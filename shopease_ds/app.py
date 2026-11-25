import sqlite3
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# ── Data Science imports (recommendation + analysis) ────────
from recommendation import (get_recommendations, get_homepage_recommendations,
                            get_behavior_recommendations)
from analysis import (get_data_summary, generate_all_charts,
                      generate_similarity_chart)

app = Flask(__name__)
app.secret_key = 'ecommerce_secret_key_2026'

# ---------------- INIT ----------------

DB_PATH = 'ecommerce.db'

ADMIN_CREDENTIALS = {
    'name': 'Rahul S S',
    'phone': '963852741',
    'email': 'wasd951@gmail.com'
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT,
        description TEXT,
        category TEXT,
        stock INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE,
        user_phone TEXT,
        name TEXT,
        phone TEXT,
        address TEXT,
        product TEXT,
        product_id INTEGER,
        price REAL,
        quantity INTEGER DEFAULT 1,
        status TEXT DEFAULT 'Booked',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        email TEXT,
        address TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1
    )''')

    # Tracks which products each logged-in user has viewed
    c.execute('''CREATE TABLE IF NOT EXISTS product_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT,
        product_id INTEGER,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Seed demo products if empty
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        demo_products = [
            ('Classic White Shirt', 799, 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400', 'Premium cotton formal shirt', 'Shirt', 25),
            ('Blue Denim Shirt', 1099, 'https://images.unsplash.com/photo-1607345366928-199ea26cfe3e?w=400', 'Casual denim shirt', 'Shirt', 18),
            ('Graphic Print T-Shirt', 499, 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400', 'Trendy graphic tee', 'T-Shirt', 40),
            ('Plain Round Neck T-Shirt', 399, 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=400', 'Everyday comfort wear', 'T-Shirt', 3),
            ('Slim Fit Pant', 1299, 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400', 'Modern slim fit trousers', 'Pant', 15),
            ('Chino Pant', 1499, 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400', 'Casual chino pants', 'Pant', 10),
            ('Formal Trousers', 1699, 'https://images.unsplash.com/photo-1594938298603-c8148c4b4c4b?w=400', 'Office wear formal trousers', 'Trousers', 8),
            ('Cotton Kurtha', 899, 'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400', 'Traditional cotton kurtha', 'Kurtha', 20),
            ('Silk Kurtha', 1899, 'https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?w=400', 'Premium silk festive kurtha', 'Kurtha', 0),
            ('Blazer Coat', 3499, 'https://images.unsplash.com/photo-1617137968427-85924c800a22?w=400', 'Professional blazer coat', 'Coat', 6),
            ('Winter Coat', 4299, 'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400', 'Warm wool winter coat', 'Coat', 4),
            ('Polo T-Shirt', 699, 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400', 'Classic polo collar tee', 'T-Shirt', 30),
        ]
        c.executemany('INSERT INTO products (name, price, image, description, category, stock) VALUES (?,?,?,?,?,?)', demo_products)

    conn.commit()
    conn.close()

def generate_order_id():
    return 'ORD' + ''.join(random.choices(string.digits, k=4))

def is_admin():
    return session.get('is_admin', False)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_phone' not in session:
            session['next'] = request.url
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------------- USER MODULE ----------------

@app.route('/')
def index():
    conn = get_db()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', 'All')

    query = 'SELECT * FROM products WHERE 1=1'
    params = []

    if search:
        query += ' AND (name LIKE ? OR description LIKE ? OR category LIKE ?)'
        s = f'%{search}%'
        params.extend([s, s, s])

    if category and category != 'All':
        query += ' AND category = ?'
        params.append(category)

    products = conn.execute(query, params).fetchall()
    categories = ['All', 'Shirt', 'T-Shirt', 'Pant', 'Trousers', 'Kurtha', 'Coat']

    cart_count = 0
    if session.get('user_phone'):
        row = conn.execute('SELECT SUM(quantity) FROM cart WHERE user_phone=?', (session['user_phone'],)).fetchone()
        cart_count = row[0] or 0

    conn.close()

    # ── Behavior-Based Recommendations for homepage ─────────
    # If user is logged in → use their order/cart/browse history
    # If not logged in    → fall back to popular products
    # Only shown when user is not actively searching/filtering
    popular_products = []
    popular_label    = ''
    if not search and category == 'All':
        user_phone = session.get('user_phone')
        browsed    = request.args.get('category', 'All')
        popular_products, popular_label = get_behavior_recommendations(
            user_phone=user_phone,
            browsed_category=browsed,
            n=8
        )

    return render_template('index.html',
                           products=products,
                           categories=categories,
                           selected_category=category,
                           search=search,
                           cart_count=cart_count,
                           popular_products=popular_products,
                           popular_label=popular_label)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    cart_count = 0
    if session.get('user_phone'):
        row = conn.execute('SELECT SUM(quantity) FROM cart WHERE user_phone=?', (session['user_phone'],)).fetchone()
        cart_count = row[0] or 0
    conn.close()

    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('index'))

    # ── Log this view for the logged-in user ─────────────────
    # Keeps only the latest 50 views per user to stay lightweight
    if session.get('user_phone'):
        conn2 = get_db()
        conn2.execute(
            'INSERT INTO product_views (user_phone, product_id) VALUES (?,?)',
            (session['user_phone'], product_id)
        )
        # Keep only latest 50 views per user — delete older ones
        conn2.execute('''
            DELETE FROM product_views WHERE user_phone=?
            AND id NOT IN (
                SELECT id FROM product_views
                WHERE user_phone=?
                ORDER BY viewed_at DESC LIMIT 50
            )
        ''', (session['user_phone'], session['user_phone']))
        conn2.commit()
        conn2.close()

    # ── Content-Based Recommendations for this product ──────
    recommendations = get_recommendations(product_id, n=6)

    return render_template('product_detail.html',
                           product=product,
                           cart_count=cart_count,
                           recommendations=recommendations)

# ---------------- AUTH MODULE ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name  = request.form.get('name',  '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        if not name or not phone or not email:
            flash('All fields are required.', 'danger')
            return render_template('login.html')

        # Check admin
        if (name  == ADMIN_CREDENTIALS['name'] and
                phone == ADMIN_CREDENTIALS['phone'] and
                email == ADMIN_CREDENTIALS['email']):
            session['user_phone'] = phone
            session['user_name']  = name
            session['user_email'] = email
            session['is_admin']   = True
            flash(f'Welcome Admin {name}!', 'success')
            return redirect(url_for('admin_dashboard'))

        # Normal user
        conn = get_db()
        existing = conn.execute('SELECT * FROM customers WHERE phone=?', (phone,)).fetchone()
        if existing:
            session['user_phone'] = phone
            session['user_name']  = existing['name']
            session['user_email'] = existing['email']
            session['is_admin']   = False
        else:
            conn.execute('INSERT INTO customers (name, phone, email) VALUES (?,?,?)', (name, phone, email))
            conn.commit()
            session['user_phone'] = phone
            session['user_name']  = name
            session['user_email'] = email
            session['is_admin']   = False
        conn.close()

        flash(f'Welcome, {name}!', 'success')
        next_url = session.pop('next', None)
        return redirect(next_url or url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# ---------------- CART MODULE ----------------

@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    items = conn.execute('''
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.image, p.stock
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_phone = ?
    ''', (session['user_phone'],)).fetchall()

    total      = sum(item['price'] * item['quantity'] for item in items)
    cart_count = sum(item['quantity'] for item in items)
    conn.close()
    return render_template('cart.html', items=items, total=total, cart_count=cart_count)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity   = int(request.form.get('quantity', 1))
    conn       = get_db()
    product    = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    if not product or product['stock'] == 0:
        flash('Product unavailable or out of stock.', 'danger')
        conn.close()
        return redirect(url_for('index'))

    existing = conn.execute('SELECT * FROM cart WHERE user_phone=? AND product_id=?',
                            (session['user_phone'], product_id)).fetchone()
    if existing:
        conn.execute('UPDATE cart SET quantity=? WHERE id=?',
                     (existing['quantity'] + quantity, existing['id']))
    else:
        conn.execute('INSERT INTO cart (user_phone, product_id, quantity) VALUES (?,?,?)',
                     (session['user_phone'], product_id, quantity))
    conn.commit()
    conn.close()
    flash(f'"{product["name"]}" added to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    cart_id = request.form.get('cart_id')
    action  = request.form.get('action')
    conn    = get_db()
    item    = conn.execute('SELECT * FROM cart WHERE id=? AND user_phone=?',
                           (cart_id, session['user_phone'])).fetchone()
    if item:
        if action == 'increase':
            conn.execute('UPDATE cart SET quantity=? WHERE id=?',
                         (item['quantity'] + 1, cart_id))
        elif action == 'decrease':
            if item['quantity'] > 1:
                conn.execute('UPDATE cart SET quantity=? WHERE id=?',
                             (item['quantity'] - 1, cart_id))
            else:
                conn.execute('DELETE FROM cart WHERE id=?', (cart_id,))
        elif action == 'remove':
            conn.execute('DELETE FROM cart WHERE id=?', (cart_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

# ---------------- ORDER MODULE ----------------

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    conn  = get_db()
    items = conn.execute('''
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.stock
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_phone = ?
    ''', (session['user_phone'],)).fetchall()

    if not items:
        flash('Your cart is empty.', 'warning')
        conn.close()
        return redirect(url_for('cart'))

    customer   = conn.execute('SELECT * FROM customers WHERE phone=?', (session['user_phone'],)).fetchone()
    total      = sum(item['price'] * item['quantity'] for item in items)
    cart_count = sum(item['quantity'] for item in items)

    if request.method == 'POST':
        address = request.form.get('address', '').strip()
        if not address:
            flash('Please enter a delivery address.', 'danger')
            return render_template('checkout.html', items=items, total=total,
                                   customer=customer, cart_count=cart_count)

        placed_orders = []
        for item in items:
            product = conn.execute('SELECT * FROM products WHERE id=?', (item['product_id'],)).fetchone()
            if not product or product['stock'] < item['quantity']:
                flash(f'"{item["name"]}" is out of stock or insufficient quantity.', 'danger')
                conn.close()
                return redirect(url_for('cart'))

            order_id = generate_order_id()
            while conn.execute('SELECT id FROM orders WHERE order_id=?', (order_id,)).fetchone():
                order_id = generate_order_id()

            conn.execute('''INSERT INTO orders
                (order_id, user_phone, name, phone, address, product, product_id, price, quantity, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (order_id, session['user_phone'], session['user_name'],
                 session['user_phone'], address, item['name'], item['product_id'],
                 item['price'] * item['quantity'], item['quantity'], 'Booked'))

            conn.execute('UPDATE products SET stock=stock-? WHERE id=?',
                         (item['quantity'], item['product_id']))
            conn.execute('UPDATE customers SET address=? WHERE phone=?',
                         (address, session['user_phone']))
            placed_orders.append(order_id)

        conn.execute('DELETE FROM cart WHERE user_phone=?', (session['user_phone'],))
        conn.commit()
        conn.close()
        flash('Order Placed Successfully! Order IDs: ' + ', '.join(placed_orders), 'success')
        return redirect(url_for('orders'))

    conn.close()
    return render_template('checkout.html', items=items, total=total,
                           customer=customer, cart_count=cart_count)

@app.route('/buy_now/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy_now(product_id):
    conn     = get_db()
    product  = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    if not product or product['stock'] == 0:
        flash('Product unavailable.', 'danger')
        conn.close()
        return redirect(url_for('index'))

    customer   = conn.execute('SELECT * FROM customers WHERE phone=?', (session['user_phone'],)).fetchone()
    quantity   = int(request.form.get('quantity', 1))
    cart_count = 0
    row        = conn.execute('SELECT SUM(quantity) FROM cart WHERE user_phone=?', (session['user_phone'],)).fetchone()
    cart_count = row[0] or 0

    if request.method == 'POST' and 'address' in request.form:
        address = request.form.get('address', '').strip()
        if not address:
            flash('Please enter a delivery address.', 'danger')
            return render_template('buy_now.html', product=product,
                                   customer=customer, quantity=quantity,
                                   cart_count=cart_count)

        order_id = generate_order_id()
        while conn.execute('SELECT id FROM orders WHERE order_id=?', (order_id,)).fetchone():
            order_id = generate_order_id()

        total_price = product['price'] * quantity
        conn.execute('''INSERT INTO orders
            (order_id, user_phone, name, phone, address, product, product_id, price, quantity, status)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (order_id, session['user_phone'], session['user_name'],
             session['user_phone'], address, product['name'], product['id'],
             total_price, quantity, 'Booked'))

        conn.execute('UPDATE products SET stock=stock-? WHERE id=?',
                     (quantity, product_id))
        conn.execute('UPDATE customers SET address=? WHERE phone=?',
                     (address, session['user_phone']))
        conn.commit()
        conn.close()
        flash(f'Order Placed Successfully! Your Order ID: {order_id}', 'success')
        return redirect(url_for('orders'))

    conn.close()
    return render_template('buy_now.html', product=product,
                           customer=customer, quantity=quantity,
                           cart_count=cart_count)

@app.route('/orders')
@login_required
def orders():
    conn        = get_db()
    user_orders = conn.execute(
        'SELECT * FROM orders WHERE user_phone=? ORDER BY created_at DESC',
        (session['user_phone'],)
    ).fetchall()
    cart_count = 0
    row        = conn.execute('SELECT SUM(quantity) FROM cart WHERE user_phone=?',
                              (session['user_phone'],)).fetchone()
    cart_count = row[0] or 0
    conn.close()
    return render_template('orders.html', orders=user_orders, cart_count=cart_count)

# ---------------- ADMIN MODULE ----------------

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_new_orders_count():
    """Helper — used by every admin page to show badge in sidebar."""
    conn  = get_db()
    count = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Booked'").fetchone()[0]
    conn.close()
    return count

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn             = get_db()
    total_products   = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_orders     = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_customers  = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    revenue          = conn.execute('SELECT SUM(price) FROM orders').fetchone()[0] or 0
    low_stock        = conn.execute('SELECT * FROM products WHERE stock < 5').fetchall()
    new_orders       = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Booked'").fetchone()[0]
    recent_orders    = conn.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           total_customers=total_customers,
                           revenue=revenue,
                           low_stock=low_stock,
                           new_orders=new_orders,
                           recent_orders=recent_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    conn     = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/products.html', products=products,
                           new_orders=get_new_orders_count())

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name        = request.form.get('name',        '').strip()
        price       = request.form.get('price',       '').strip()
        description = request.form.get('description', '').strip()
        image       = request.form.get('image',       '').strip()
        category    = request.form.get('category',    '').strip()
        stock       = request.form.get('stock',       '0').strip()

        if not name or not price or not category:
            flash('Name, price, and category are required.', 'danger')
            return render_template('admin/product_form.html',
                                   product=None, action='Add',
                                   new_orders=get_new_orders_count())

        conn = get_db()
        conn.execute(
            'INSERT INTO products (name, price, image, description, category, stock) VALUES (?,?,?,?,?,?)',
            (name, float(price),
             image or 'https://via.placeholder.com/400x400?text=No+Image',
             description, category, int(stock))
        )
        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html', product=None, action='Add',
                           new_orders=get_new_orders_count())

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    conn    = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    if not product:
        flash('Product not found.', 'danger')
        conn.close()
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        name        = request.form.get('name',        '').strip()
        price       = request.form.get('price',       '').strip()
        description = request.form.get('description', '').strip()
        image       = request.form.get('image',       '').strip()
        category    = request.form.get('category',    '').strip()
        stock       = request.form.get('stock',       '0').strip()

        conn.execute(
            'UPDATE products SET name=?, price=?, image=?, description=?, category=?, stock=? WHERE id=?',
            (name, float(price), image, description, category, int(stock), product_id)
        )
        conn.commit()
        conn.close()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))

    conn.close()
    return render_template('admin/product_form.html', product=product, action='Edit',
                           new_orders=get_new_orders_count())

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?', (product_id,))
    conn.commit()
    conn.close()
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))

# ---------------- ADMIN ORDERS ----------------

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn      = get_db()
    booked    = conn.execute("SELECT * FROM orders WHERE status='Booked'    ORDER BY created_at DESC").fetchall()
    shipping  = conn.execute("SELECT * FROM orders WHERE status='Shipping'  ORDER BY created_at DESC").fetchall()
    delivered = conn.execute("SELECT * FROM orders WHERE status='Delivered' ORDER BY created_at DESC").fetchall()
    new_orders = len(booked)
    conn.close()
    return render_template('admin/orders.html',
                           booked=booked, shipping=shipping,
                           delivered=delivered, new_orders=new_orders)

@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    new_status = request.form.get('status')
    valid      = ['Booked', 'Shipping', 'Delivered']
    if new_status in valid:
        conn = get_db()
        conn.execute('UPDATE orders SET status=? WHERE id=?', (new_status, order_id))
        conn.commit()
        conn.close()
        flash(f'Order status updated to {new_status}.', 'success')
    return redirect(url_for('admin_orders'))

# ---------------- ADMIN CUSTOMERS ----------------

@app.route('/admin/customers')
@admin_required
def admin_customers():
    conn      = get_db()
    customers = conn.execute('''
        SELECT c.*, COUNT(o.id) as order_count
        FROM customers c
        LEFT JOIN orders o ON c.phone = o.user_phone
        GROUP BY c.id ORDER BY order_count DESC
    ''').fetchall()
    total = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    conn.close()
    return render_template('admin/customers.html', customers=customers,
                           total=total, new_orders=get_new_orders_count())

# ---------------- ADMIN ANALYSIS (DATA SCIENCE) ----------------

@app.route('/admin/analysis')
@admin_required
def admin_analysis():
    """
    Data Science analytics page.
    Generates all charts fresh on each visit so they always
    reflect the current product catalogue.
    """
    summary    = get_data_summary()
    charts     = generate_all_charts()
    new_orders = get_new_orders_count()

    # Load all products for the similarity dropdown
    conn         = get_db()
    all_prods_db = conn.execute('SELECT id, name FROM products ORDER BY name').fetchall()
    conn.close()

    all_products = [(row['id'], row['name']) for row in all_prods_db]

    # Generate default similarity chart for the first product
    sim_chart        = None
    sim_product_name = ''
    if all_products:
        first_id, first_name = all_products[0]
        sim_chart        = generate_similarity_chart(first_id, first_name)
        sim_product_name = first_name

    return render_template('admin/analysis.html',
                           summary=summary,
                           charts=charts,
                           sim_chart=sim_chart,
                           sim_product_name=sim_product_name,
                           all_products=all_products,
                           new_orders=new_orders)

@app.route('/admin/analysis/similarity/<int:product_id>')
@admin_required
def admin_similarity(product_id):
    """
    AJAX / direct route to regenerate the similarity chart
    for a specific product_id.
    Returns JSON with the chart URL and product name.
    """
    conn    = get_db()
    product = conn.execute('SELECT id, name FROM products WHERE id=?', (product_id,)).fetchone()
    conn.close()

    if not product:
        return jsonify({'error': 'Product not found'}), 404

    chart_url = generate_similarity_chart(product['id'], product['name'])
    return jsonify({
        'chart_url':    chart_url or '',
        'product_name': product['name']
    })

# ── API endpoint — returns recommendations as JSON ──────────
@app.route('/api/recommendations/<int:product_id>')
def api_recommendations(product_id):
    """
    JSON API: returns up to 6 recommendations for product_id.
    Useful for future AJAX-based loading.
    """
    recs = get_recommendations(product_id, n=6)
    return jsonify({'product_id': product_id, 'recommendations': recs})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
