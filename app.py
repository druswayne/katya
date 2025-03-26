from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
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
    image_path = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    message = db.Column(db.Text, nullable=False)
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
    return render_template('admin/dashboard.html')

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/products')
@login_required
def admin_products():
    categories = Category.query.order_by(Category.title).all()
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', categories=categories, products=products)

def generate_unique_filename(original_filename):
    """Генерирует уникальное имя файла"""
    # Получаем расширение файла
    ext = os.path.splitext(original_filename)[1].lower()
    # Генерируем уникальное имя с помощью UUID и временной метки
    unique_filename = f"{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    return unique_filename

@app.route('/admin/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'GET':
        return render_template('admin/add_category.html')
        
    title = request.form.get('title')
    description = request.form.get('description')
    image = request.files.get('image')
    
    if not title:
        flash('Название категории обязательно')
        return redirect(url_for('admin_categories'))
    
    try:
        new_category = Category(title=title, description=description)
        db.session.add(new_category)
        db.session.commit()
        
        if image:
            # Генерируем уникальное имя файла
            filename = generate_unique_filename(image.filename)
            # Сохраняем файл
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Обновляем путь к изображению в базе данных
            new_category.image_path = filename
            db.session.commit()
        
        flash('Категория успешно добавлена')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при добавлении категории')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('admin/edit_category.html', category=category)
        
    title = request.form.get('title')
    description = request.form.get('description')
    image = request.files.get('image')
    
    if not title:
        flash('Название категории обязательно')
        return redirect(url_for('admin_categories'))
    
    try:
        category.title = title
        category.description = description
        
        if image:
            # Удаляем старое изображение, если оно есть
            if category.image_path:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image_path)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Генерируем уникальное имя файла
            filename = generate_unique_filename(image.filename)
            # Сохраняем новый файл
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Обновляем путь к изображению в базе данных
            category.image_path = filename
        
        db.session.commit()
        flash('Категория успешно обновлена')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при обновлении категории')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/category/delete/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    
    try:
        # Удаляем все товары в категории
        products = Product.query.filter_by(category_id=id).all()
        for product in products:
            # Удаляем изображения товаров
            if product.image_path:
                product_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_path)
                if os.path.exists(product_image_path):
                    os.remove(product_image_path)
            db.session.delete(product)
        
        # Удаляем изображение категории
        if category.image_path:
            category_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image_path)
            if os.path.exists(category_image_path):
                os.remove(category_image_path)
        
        # Удаляем категорию
        db.session.delete(category)
        db.session.commit()
        flash('Категория и все связанные товары успешно удалены')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при удалении категории')
    
    return redirect(url_for('admin_categories'))

@app.route('/category/<int:id>')
def category_products(id):
    category = Category.query.get_or_404(id)
    products = Product.query.filter_by(category_id=id).order_by(Product.created_at.desc()).all()
    return render_template('category_products.html', category=category, products=products)

@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    category_id = request.form.get('category_id')
    image = request.files.get('image')
    
    if not all([title, description, price, category_id]):
        flash('Пожалуйста, заполните все обязательные поля')
        return redirect(url_for('admin_products'))
    
    try:
        new_product = Product(
            title=title,
            description=description,
            price=float(price),
            category_id=category_id
        )
        db.session.add(new_product)
        db.session.commit()
        
        if image:
            # Генерируем уникальное имя файла
            filename = generate_unique_filename(image.filename)
            # Сохраняем файл
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Обновляем путь к изображению в базе данных
            new_product.image_path = filename
            db.session.commit()
        
        flash('Товар успешно добавлен')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при добавлении товара')
    
    return redirect(url_for('admin_products'))

@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    categories = Category.query.order_by(Category.title).all()
    
    if request.method == 'GET':
        return render_template('admin/edit_product.html', product=product, categories=categories)
        
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    category_id = request.form.get('category_id')
    image = request.files.get('image')
    is_active = 'is_active' in request.form
    
    if not all([title, description, price, category_id]):
        flash('Пожалуйста, заполните все обязательные поля')
        return redirect(url_for('admin_products'))
    
    try:
        product.title = title
        product.description = description
        product.price = float(price)
        product.category_id = category_id
        product.is_active = is_active
        
        if image:
            # Удаляем старое изображение, если оно есть
            if product.image_path:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_path)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Генерируем уникальное имя файла
            filename = generate_unique_filename(image.filename)
            # Сохраняем новый файл
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Обновляем путь к изображению в базе данных
            product.image_path = filename
        
        db.session.commit()
        flash('Товар успешно обновлен')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при обновлении товара')
    
    return redirect(url_for('admin_products'))

@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
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
    return redirect(url_for('admin_products'))

@app.route('/product/<int:id>')
def product_details(id):
    product = Product.query.get_or_404(id)
    if not product.is_active:
        flash('Товар временно недоступен')
        return redirect(url_for('category_products', id=product.category_id))
    return render_template('product_details.html', product=product)

@app.route('/order/<int:product_id>', methods=['POST'])
def order_product(product_id):
    product = Product.query.get_or_404(product_id)
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    if not all([name, email, phone]):
        flash('Пожалуйста, заполните все поля')
        return redirect(url_for('product_details', id=product_id))
    
    try:
        message = f"Заказ товара:\nНазвание: {product.title}\nКатегория: {product.category.title}\nЦена: {product.price} руб.\n\nДанные заказчика:\nИмя: {name}\nEmail: {email}\nТелефон: {phone}"
        new_message = Message(name=name, email=email, phone=phone, message=message)
        db.session.add(new_message)
        db.session.commit()
        flash('Спасибо за ваш заказ! Мы свяжемся с вами в ближайшее время.')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте позже.')
    
    return redirect(url_for('product_details', id=product_id))

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    message = request.form.get('message')
    
    if not all([name, email, message]):
        flash('Пожалуйста, заполните все обязательные поля')
        return redirect(url_for('index', _anchor='contacts'))
    
    try:
        new_message = Message(name=name, email=email, phone=phone, message=message)
        db.session.add(new_message)
        db.session.commit()
        flash('Спасибо за ваше сообщение! Мы свяжемся с вами в ближайшее время.')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.')
    
    return redirect(url_for('index', _anchor='contacts'))

@app.route('/admin/messages')
@login_required
def admin_messages():
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)

@app.route('/admin/message/delete/<int:id>')
@login_required
def delete_message(id):
    message = Message.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    flash('Сообщение успешно удалено')
    return redirect(url_for('admin_messages'))

# Создание базы данных и администратора
def init_db():
    with app.app_context():
        db.create_all()
        # Создаем администратора, если его нет
        if not User.query.first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('2wMbyKAP')
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    # Создаем папку для загрузок, если её нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    app.run(debug=True) 