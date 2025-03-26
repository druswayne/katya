from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# Модели данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    image_path = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршруты для главной страницы
@app.route('/')
def index():
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('index.html', categories=categories)

# Маршруты для администратора
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Неверное имя пользователя или пароль')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('admin/dashboard.html', categories=categories)

@app.route('/admin/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image = request.files.get('image')
        
        if image:
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}"
            # Сохраняем только имя файла, без папки uploads
            image_path = filename
            # Сохраняем файл в папку uploads
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            image_path = None
            
        category = Category(
            title=title,
            description=description,
            image_path=image_path
        )
        db.session.add(category)
        db.session.commit()
        flash('Категория успешно добавлена')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_category.html')

@app.route('/admin/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        category.title = request.form.get('title')
        category.description = request.form.get('description')
        image = request.files.get('image')
        
        if image:
            if category.image_path:
                try:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except:
                    pass
            
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}"
            # Сохраняем только имя файла
            category.image_path = filename
            # Сохраняем файл в папку uploads
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        db.session.commit()
        flash('Категория успешно обновлена')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_category.html', category=category)

@app.route('/admin/category/delete/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if category.image_path:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
    db.session.delete(category)
    db.session.commit()
    flash('Категория успешно удалена')
    return redirect(url_for('admin_dashboard'))

@app.route('/category/<int:id>')
def category_products(id):
    category = Category.query.get_or_404(id)
    products = Product.query.filter_by(category_id=id).order_by(Product.created_at.desc()).all()
    return render_template('category_products.html', category=category, products=products)

@app.route('/admin/product/add/<int:category_id>', methods=['GET', 'POST'])
@login_required
def add_product(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        image = request.files.get('image')
        
        if image:
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}"
            image_path = filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            image_path = None
            
        product = Product(
            title=title,
            description=description,
            price=price,
            image_path=image_path,
            category_id=category_id
        )
        db.session.add(product)
        db.session.commit()
        flash('Товар успешно добавлен')
        return redirect(url_for('category_products', id=category_id))
    return render_template('admin/add_product.html', category=category)

@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.title = request.form.get('title')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price', 0))
        image = request.files.get('image')
        
        if image:
            if product.image_path:
                try:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except:
                    pass
            
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}"
            product.image_path = filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        db.session.commit()
        flash('Товар успешно обновлен')
        return redirect(url_for('category_products', id=product.category_id))
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    category_id = product.category_id
    if product.image_path:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
    db.session.delete(product)
    db.session.commit()
    flash('Товар успешно удален')
    return redirect(url_for('category_products', id=category_id))

# Создание базы данных и администратора
def init_db():
    with app.app_context():
        db.create_all()
        # Создаем администратора, если его нет
        if not User.query.first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    # Создаем папку для загрузок, если её нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    app.run(debug=True) 