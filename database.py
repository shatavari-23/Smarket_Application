from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    date_joined = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    products = db.relationship('Product', back_populates='seller')
    orders = db.relationship('Order', back_populates='user')
    cart = db.relationship('Cart', back_populates='user', uselist=False)
    notifications = db.relationship('Notification', back_populates='user')
    wishlist = db.relationship('Wishlist', back_populates='user', uselist=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', back_populates='products')

    reviews = db.relationship('Review', back_populates='product', cascade="all, delete-orphan")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    shipping_address = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    estimated_delivery_date = db.Column(db.DateTime, nullable=False)

    payment_method = db.Column(db.String(50), nullable=False)
    payment_details = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(50), nullable=False, default='Processing')
    tracking_number = db.Column(db.String(100), nullable=True)

    invoice_generated = db.Column(db.Boolean, default=False, nullable=False)

    items = db.relationship('OrderItem', backref='order', lazy=True)
    user = db.relationship('User', back_populates='orders')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', lazy=True)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', back_populates='cart')


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)

    cart = db.relationship('Cart', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref='cart_items')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(255), nullable=False)

    is_read = db.Column(db.Boolean, default=False, nullable=False)

    redirect_url = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(50), default='default', nullable=False)

    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User', back_populates='notifications')


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', back_populates='wishlist')

    items = db.relationship('WishlistItem', backref='wishlist', lazy=True)


class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    product = db.relationship('Product')


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)

    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User')
    product = db.relationship('Product', back_populates='reviews')


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])
    product = db.relationship('Product')

    messages = db.relationship('Message', back_populates='conversation', cascade="all, delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)

    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)

    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    is_read = db.Column(db.Boolean, default=False, nullable=False)

    conversation = db.relationship('Conversation', back_populates='messages')

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, unique=True)

    amount = db.Column(db.Float, nullable=False)

    payment_method = db.Column(db.String(50), nullable=False)

    status = db.Column(db.String(50), nullable=False, default='pending')

    transaction_id = db.Column(db.String(100), nullable=True)

    payment_date = db.Column(db.DateTime, nullable=True)

    order = db.relationship('Order', backref=db.backref('payment', uselist=False))

    def __repr__(self):
        return f'<Payment {self.id} for Order {self.order_id}>'


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user_role = db.Column(db.String(50), nullable=False)

    rating = db.Column(db.Integer, nullable=False)

    feedback_text = db.Column(db.Text, nullable=False)

    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin_reply = db.Column(db.Text, nullable=True)

    replied_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))