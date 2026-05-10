from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci_rahasia_logistik'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///logistics.db'

# Inisialisasi Database & Login
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Buyer')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    stok = db.Column(db.Integer, nullable=False)
    img = db.Column(db.String(200), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.Column(db.String(500), nullable=False)
    total_harga = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Diproses')
    resi = db.Column(db.String(100), default='-')
    metode_pembayaran = db.Column(db.String(50)) # KOLOM INI WAJIB ADA

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 2. DATA DUMMY ---
products_list = [
    {'id': 'COF-001', 'nama': 'Java Bold Robusta', 'harga': 66053, 'stok': 12, 'img': 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500'},
    {'id': 'COF-002', 'nama': 'Arabika Ijen Full Wash', 'harga': 38129, 'stok': 20, 'img': 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500'},
    {'id': 'COF-003', 'nama': 'Mandheling Sumatra Specialty', 'harga': 75000, 'stok': 15, 'img': 'https://images.unsplash.com/photo-1611854779393-1b2da9d400fe?w=500'},
    {'id': 'COF-004', 'nama': 'Toraja Sapan Grade 1', 'harga': 82000, 'stok': 10, 'img': 'https://images.unsplash.com/photo-1511537190424-bbbab87ac5eb?w=500'},
]

cart = []

# --- 3. ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    db_products = Product.query.all()
    # Gabungkan kopi lama + database
    all_products = products_list + [
        {'id': p.id, 'nama': p.nama, 'harga': p.harga, 'stok': p.stok, 'img': p.img} 
        for p in db_products
    ]

    if request.method == 'POST':
        # FITUR SELLER: TAMBAH STOK
        if 'tambah_produk' in request.form and current_user.role == 'Seller':
            new_p = Product(
                nama=request.form.get('nama'),
                harga=int(request.form.get('harga')),
                stok=int(request.form.get('stok')),
                img="https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500"
            )
            db.session.add(new_p)
            db.session.commit()
            flash("Produk berhasil ditambah!", "success")

        # FITUR BUYER: ADD TO CART
        elif 'add_to_cart' in request.form:
            p_id = request.form.get('product_id')
            product = next((p for p in all_products if str(p['id']) == str(p_id)), None)
            if product: 
                cart.append(product)
                flash(f"{product['nama']} masuk keranjang", "success")
        return redirect(url_for('index'))
    
    total_cart = sum(item['harga'] for item in cart)
    return render_template('index.html', products=all_products, cart=cart, total_cart=total_cart)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login Berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Gagal! Cek email dan password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') # Menangkap role dari dropdown register

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email sudah terdaftar!', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        # Simpan user dengan role pilihan
        user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Akun berhasil dibuat! Silakan Login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/cart.html')
def cart_page():
    total = sum(item['harga'] for item in cart)
    return render_template('cart.html', cart=cart, total=total)

@app.route('/checkout_page')
@login_required
def checkout_page():
    subtotal = sum(item['harga'] for item in cart)
    # Tentukan nilai ongkir di sini agar tidak 'Undefined'
    ongkir = 10000 
    layanan = 2000
    total_akhir = subtotal + ongkir + layanan
    
    # Pastikan semua variabel ini ditulis di dalam render_template
    return render_template('checkout.html', 
                           cart=cart, 
                           subtotal=subtotal, 
                           ongkir=ongkir, 
                           layanan=layanan, 
                           total=total_akhir)

# 1. Rute untuk MENAMPILKAN halaman form retur
@app.route('/return.html')
def return_page():
    return render_template('return.html')

# 2. Rute untuk MEMPROSES data saat tombol diklik
@app.route('/proses_retur', methods=['POST'])
@login_required
def proses_retur():
    nomor_resi = request.form.get('nomor_resi')
    alasan = request.form.get('alasan')
    
    if nomor_resi and alasan:
        flash(f'Permintaan retur untuk resi {nomor_resi} diajukan.', 'info')
        return redirect(url_for('index'))
    
    flash('Mohon isi semua data!', 'danger')
    return redirect(url_for('return_page'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/proses_pesanan', methods=['POST'])
@login_required
def proses_pesanan():
    global cart
    # Ambil metode dari form checkout
    metode = request.form.get('payment_method') 
    
    items_name = ", ".join([item['nama'] for item in cart])
    subtotal = sum(item['harga'] for item in cart)
    
    order = Order(
        user_id=current_user.id,
        items=items_name,
        total_harga=subtotal + 12000, # Subtotal + Ongkir
        status='Diproses',
        resi='-',
        metode_pembayaran=metode # PASTIKAN INI MASUK
    )
    db.session.add(order)
    db.session.commit()
    cart = [] 
    flash(f'Pesanan berhasil dibuat!', 'success')
    return redirect(url_for('index'))

@app.route('/track')
@login_required
def track_orders():
    # Ambil semua pesanan milik user yang sedang login
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('track.html', orders=user_orders)

@app.route('/logistics_dashboard', methods=['GET', 'POST'])
@login_required
def logistics_dashboard():
    if current_user.role != 'Logistics':
        flash("Akses ditolak! Khusus Pihak Logistik.", "danger")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        baru_status = request.form.get('status')
        baru_resi = request.form.get('resi')
        
        order = Order.query.get(order_id)
        if order:
            order.status = baru_status
            order.resi = baru_resi
            db.session.commit()
            flash(f"Pesanan #{order_id} berhasil diupdate!", "success")
            
    orders = Order.query.all()
    return render_template('logistics_dashboard.html', orders=orders)

@app.route('/submit_return', methods=['POST'])
def submit_return():
    item = request.form.get('item_name')
    reason = request.form.get('reason')
    # Di sini kamu bisa simpan ke database atau kirim notifikasi ke admin
    flash(f"Permintaan retur untuk {item} berhasil dikirim!", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Tambahkan host='0.0.0.0' untuk memastikan akses terbuka
    app.run(debug=True, host='127.0.0.1', port=5000)