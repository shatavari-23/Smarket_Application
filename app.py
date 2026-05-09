from flask import Flask, render_template, request, jsonify, make_response, flash, redirect, url_for
from flask_socketio import SocketIO, join_room, emit
from datetime import datetime, timezone
import logging
from sqlalchemy import or_, func, extract
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from werkzeug.utils import secure_filename
from database import db, User, Product, Order, OrderItem, Cart, CartItem, Notification, Wishlist, WishlistItem, Review, Conversation, Message, Payment, Feedback
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = '1a6dcac2f3b044e21bb592a42fdb8b35'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/products'
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_view = 'index'  # Redirect to index page
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

user_sids = {}

# Configure basic logging for debug purposes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect(auth=None):
    if current_user.is_authenticated:
        # Each user joins a room named after their user ID.
        # This allows sending notifications to all of a user's connected clients (e.g., in different tabs).
        join_room(f'user_{current_user.id}')
        # Have admins join a special room
        if current_user.role == 'admin':
            join_room('admin_room')

@socketio.on('disconnect')
def handle_disconnect():
    # Rooms are left automatically on disconnect, but you can add custom logic here if needed.
    pass

def create_and_send_notification(user_id=None, room=None, title=None, message=None, type='default', redirect_url=None):
    """Helper function to create a notification and send it via Socket.IO."""
    # Ensure we don't try to create notifications for anonymous users
    if user_id and not db.session.get(User, user_id):
        return

    notification = None
    if user_id:
        notification = Notification(user_id=user_id, title=title, message=message, type=type, redirect_url=redirect_url)
        db.session.add(notification)
        db.session.commit()

    payload_base = {
        'title': title, 'message': message, 'type': type,
        'timestamp': datetime.now(timezone.utc).isoformat(), 'is_read': False, 'redirect_url': redirect_url
    }
    payload = payload_base.copy()
    if notification:
        payload['id'] = notification.id

    if room:
        socketio.emit('new_notification', payload, room=room)
    elif user_id:
        # Emit to the user's personal room
        socketio.emit('new_notification', payload, room=f'user_{user_id}')

@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    # Prevent loading soft-deleted users
    if not user:
        return None
    if getattr(user, 'is_deleted', False):
        return None
    return user

# Register route blueprints (split modules)
from routes.main import main_bp
app.register_blueprint(main_bp)
# Register compatibility endpoints for routes moved into the `main` blueprint.
# This inspects the app's URL map (after blueprint registration) and creates
# app-level endpoints with the same names (e.g. `product`, `search`, etc.) so
# existing templates that call `url_for('product')` keep working.
for rule in list(app.url_map.iter_rules()):
    # We only care about rules provided by the `main` blueprint (endpoint starts with 'main.')
    if not rule.endpoint.startswith('main.'):
        continue

    # Derive legacy endpoint name (strip the blueprint prefix)
    legacy_name = rule.endpoint.split('.', 1)[1]

    # Skip the static endpoint or already-present names
    if legacy_name == 'static' or legacy_name in app.view_functions:
        continue

    # Create a view factory to avoid late-binding closure issues
    def make_view(target_endpoint):
        def view(**kwargs):
            # Delegate to the blueprint view function by its full endpoint name
            return app.view_functions[target_endpoint](**kwargs)
        return view

    try:
        app.add_url_rule(rule.rule, endpoint=legacy_name, view_func=make_view(rule.endpoint), methods=list(rule.methods))
    except Exception:
        # If adding the rule fails for any reason, skip it silently to avoid startup crash.
        # We'll still preserve the main blueprint routes (they are already registered).
        pass

# Additional aliases used by templates that don't match the blueprint function names.
# Map alias endpoint -> existing app-level endpoint (created above from blueprint rules)
alias_map = {
    'category_page': 'category',
    'product_detail': 'product'
}
for alias, target in alias_map.items():
    if alias in app.view_functions:
        continue
    if target not in app.view_functions:
        continue
    # Find the URL rule for the target endpoint (either app-level or blueprint-prefixed)
    target_rule = None
    for r in app.url_map.iter_rules():
        if r.endpoint == target or r.endpoint == f'main.{target}':
            target_rule = r
            break
    if not target_rule:
        continue
    try:
        app.add_url_rule(target_rule.rule, endpoint=alias, view_func=app.view_functions[target], methods=list(target_rule.methods))
    except Exception:
        pass


@app.route('/api/session-check')
def session_check():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True, 'user': {'name': current_user.name, 'role': current_user.role, 'address': current_user.address}})
    return jsonify({'logged_in': False})


@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can add products'}), 403

    name = request.form.get('name')
    price = request.form.get('price')
    category = request.form.get('category')
    description = request.form.get('description')
    stock = request.form.get('stock')
    image = request.files.get('image')

    if not all([name, price, category, description, stock, image]):
        return jsonify({'success': False, 'message': 'All fields including stock are required'}), 400

    filename = secure_filename(image.filename)
    if not filename:
        return jsonify({'success': False, 'message': 'Invalid filename'}), 400

    relative_image_path = f"images/products/{filename}"
    full_save_path = os.path.join(app.root_path, 'static', 'images', 'products', filename)
    os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
    image.save(full_save_path)

    new_product = Product(
        name=name,
        price=float(price),
        category=category,
        description=description,
        image=relative_image_path,
        seller_id=current_user.id,
        stock=int(stock)
    )
    db.session.add(new_product)
    db.session.commit()

    # Notify all admins about the new pending product
    admins = User.query.filter_by(role='admin').all()
    admin_notification_message = f"Seller '{current_user.name}' has submitted a new product '{new_product.name}' for approval."
    for admin in admins:
        create_and_send_notification(
            user_id=admin.id,
            title='New Product for Approval',
            message=admin_notification_message,
            redirect_url=url_for('admin_dashboard') + '#pending-products'
        )

    return jsonify({'success': True, 'message': 'Product added successfully and is pending approval'}), 201

@app.route('/edit_product/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can edit products'}), 403

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only edit your own products'}), 403

    product.name = request.form.get('name', product.name)
    product.price = float(request.form.get('price', product.price))
    product.category = request.form.get('category', product.category)
    product.description = request.form.get('description', product.description)
    product.stock = int(request.form.get('stock', product.stock))

    # Handle new image upload
    image = request.files.get('image')
    if image:
        # Delete old image file if it exists
        if product.image:
            old_image_path = os.path.join(app.root_path, 'static', product.image)
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError:
                    pass # Ignore if deletion fails

        filename = secure_filename(image.filename)
        relative_image_path = f"images/products/{filename}"
        full_save_path = os.path.join(app.root_path, 'static', 'images', 'products', filename)
        os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
        image.save(full_save_path)
        product.image = relative_image_path

    # Product status should be reset to pending for admin review
    product.status = 'pending'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Product updated successfully and is pending re-approval'})

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    fullname = data.get('fullname')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=fullname, email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    if new_user.role == 'seller':
        # Notify all admins about the new seller
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            create_and_send_notification(
                user_id=admin.id,
                title='New Seller Registered',
                message=f"A new seller, '{new_user.name}', has registered.",
                redirect_url=url_for('admin_dashboard') + '#manage-sellers'
            )

    return jsonify({'message': 'Signed up successfully! Please log in.'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        redirect_url = '/'
        if user.role == 'admin':
            redirect_url = '/admin-dashboard#admin-reports'
        elif user.role == 'seller':
            redirect_url = '/seller-dashboard'
        response = make_response(jsonify({'message': 'Logged in successfully!', 'redirect': redirect_url}), 200)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    # Redirect with a parameter to signal the frontend to show the login form
    return redirect(url_for('index', logout='true'))

@app.route('/')
def index():
    # Mock VPN data (replace with real data/logic later)
    connection_status = {
        'status': 'Disconnected',
        'ip': 'N/A',
        'name': 'N/A',
        'gt_status': 'N/A'
    }
    vpn_list = [
        {'name': 'US East Server', 'location': 'New York, USA'},
        {'name': 'US West Server', 'location': 'Los Angeles, USA'},
        {'name': 'EU Server', 'location': 'London, UK'},
        {'name': 'Asia Server', 'location': 'Singapore'}
    ]
    is_authenticated = current_user.is_authenticated if 'current_user' in globals() else False
    client_hwid = 'HWID-12345-ABCDE' if is_authenticated else 'N/A'
    license_expires_at = '2025-12-31' if is_authenticated else 'N/A'
    error = None  # Set if there's an error, e.g., flash messages

    products = Product.query.filter_by(status='approved').all()
    return render_template('index.html', connection_status=connection_status, vpn_list=vpn_list, is_authenticated=is_authenticated, client_hwid=client_hwid, license_expires_at=license_expires_at, error=error, products=products)

@app.route('/index')
def home():
    products = Product.query.filter_by(status='approved').all()
    return render_template('index.html', products=products)

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    return render_template('admin-dashboard.html')

@app.route('/seller-dashboard')
@login_required
def seller_dashboard():
    return render_template('seller-dashboard.html')


@app.route('/chat/<int:conversation_id>')
@login_required
def chat_page(conversation_id):
    # You might want to add a check here to ensure the current_user is part of this conversation
    return render_template('chat.html', conversation_id=conversation_id, current_user_id=current_user.id, current_user_name=current_user.name, current_user_role=current_user.role)


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    user_feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.timestamp.desc()).all()
    if request.method == 'POST':
        data = request.get_json()
        rating = data.get('rating')
        feedback_text = data.get('feedback_text')

        if not rating or not feedback_text:
            return jsonify({'success': False, 'message': 'Rating and feedback text are required.'}), 400

        new_feedback = Feedback(
            user_id=current_user.id,
            user_role=current_user.role,
            rating=int(rating),
            feedback_text=feedback_text
        )
        db.session.add(new_feedback)
        db.session.commit()

        # Notify all admins about the new feedback
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            create_and_send_notification(
                user_id=admin.id,
                title='New Feedback Received',
                message=f"New feedback submitted by {current_user.name} ({current_user.role}).",
                redirect_url=url_for('admin_dashboard') + '#manage-feedback'
            )

        return jsonify({'success': True, 'message': 'Thank you for your feedback!'}), 201

    return render_template('feedback.html', user_feedbacks=user_feedbacks)

@app.route('/pending_products')
@login_required
def pending_products():
    if current_user.role != 'admin':
        return jsonify({'message': 'Only admins can view pending products'}), 403

    products = Product.query.filter_by(status='pending').all()
    product_list = []
    for product in products:
        product_list.append({
            'id': int(product.id),
            'name': product.name,
            'price': product.price,
            'category': product.category,
            'description': product.description,
            'image': '/static/' + product.image,
            'seller_id': int(product.seller_id)
        })

    return jsonify(product_list)

@app.route('/approve_product/<int:product_id>', methods=['POST'])
@login_required
def approve_product(product_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can approve products'}), 403

    product = Product.query.get_or_404(product_id)
    product.status = 'approved'
    db.session.commit()

    # Notify the seller that their product was approved
    create_and_send_notification(
        user_id=product.seller_id,
        title='Product Approved!',
        message=f"Congratulations! Your product '{product.name}' has been approved and is now live.",
        redirect_url=url_for('seller_dashboard') + '#my-products'
    )

    # Notify all buyers about the new product
    buyers = User.query.filter_by(role='buyer').all()
    for buyer in buyers:
        create_and_send_notification(
            user_id=buyer.id,
            title='New Arrival!',
            message=f"Check out the newly added product: '{product.name}'.",
            redirect_url=url_for('product', product_id=product.id)
        )

    return jsonify({'success': True, 'message': 'Product approved successfully'})

@app.route('/reject_product/<int:product_id>', methods=['POST'])
@login_required
def reject_product(product_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can reject products'}), 403

    product = Product.query.get_or_404(product_id)
    product.status = 'rejected'
    db.session.commit()

    # Notify the seller that their product was rejected
    create_and_send_notification(
        user_id=product.seller_id,
        title='Product Update',
        message=f"Your product '{product.name}' has been rejected. Please review and resubmit if necessary.",
        redirect_url=url_for('seller_dashboard') + '#my-products'
    )

    return jsonify({'success': True, 'message': 'Product rejected successfully'})

@app.route('/my_products')
@login_required
def my_products():
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can view their products'}), 403

    products = Product.query.filter_by(seller_id=current_user.id).all()
    product_list = []
    for product in products:
        product_list.append({
            'id': int(product.id),
            'name': product.name,
            'price': product.price,
            'category': product.category,
            'description': product.description,
            'image': product.image,
            'status': product.status,
            'stock': int(product.stock)
        })

    return jsonify(product_list)

@app.route('/seller_orders')
@login_required
def seller_orders():
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can view their orders'}), 403

    # Get all products by this seller
    seller_products = Product.query.filter_by(seller_id=current_user.id).all()
    product_ids = [p.id for p in seller_products]

    # Get orders that contain these products
    orders = db.session.query(Order).filter(db.session.query(OrderItem).filter(OrderItem.order_id == Order.id, OrderItem.product_id.in_(product_ids)).exists()).distinct().all()

    order_list = []
    for order in orders:
        buyer = User.query.get(order.user_id)
        items = []
        for item in order.items:
            if item.product_id in product_ids:
                items.append({
                    'name': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'image': '/static/' + item.product.image
                })
        order_list.append({
            'id': int(order.id),
            'buyer_name': buyer.name if buyer else 'Unknown',
            'date': order.order_date.isoformat() if order.order_date else None,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'total': sum(item['price'] * item['quantity'] for item in items),
            'items': items
        })

    return jsonify(order_list)

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can update order status'}), 403

    data = request.get_json()
    new_status = data.get('status')
    tracking_number = data.get('tracking_number')
    if not new_status:
        return jsonify({'success': False, 'message': 'New status is required'}), 400

    order = Order.query.get_or_404(order_id)

    # Security check: Ensure the current seller has a product in this order
    seller_product_ids = [p.id for p in current_user.products]
    is_seller_in_order = any(item.product_id in seller_product_ids for item in order.items)

    if not is_seller_in_order:
        return jsonify({'success': False, 'message': 'You are not authorized to update this order'}), 403

    current_status = order.status

    # Define the valid order of statuses
    status_hierarchy = {
        'Processing': 1,
        'Shipped': 2,
        'Delivered': 3
    }

    # Prevent updates on terminal statuses
    if current_status in ['Delivered', 'Cancelled']:
        return jsonify({'success': False, 'message': f"Order is already '{current_status}' and cannot be updated."}), 400

    current_level = status_hierarchy.get(current_status, 0)
    new_level = status_hierarchy.get(new_status, 0)

    if new_level <= current_level:
        return jsonify({'success': False, 'message': f"Cannot change status from '{current_status}' to '{new_status}'."}), 400

    order.status = new_status
    notification_message = f"The status of your order #{order.id} has been updated to '{new_status}'."

    if new_status == 'Shipped':
        order.tracking_number = tracking_number
        if tracking_number:
            notification_message += f" Your tracking number is: {tracking_number}."

    db.session.commit()

    # Notify the buyer about the status update
    create_and_send_notification(
        user_id=order.user_id,
        title='Order Status Updated',
        message=notification_message,
        redirect_url=url_for('my_orders')
    )

    return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})



@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Only sellers can delete products'}), 403

    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only delete your own products'}), 403

    # Delete image file if exists
    if product.image:
        image_path = os.path.join(app.root_path, 'static', product.image)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass  # Ignore if file deletion fails

    db.session.delete(product)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Product deleted successfully'})

@app.route('/all_products')
@login_required
def all_products():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can view all products'}), 403

    products = Product.query.all()
    product_list = []
    for product in products:
        product_list.append({
            'id': int(product.id),
            'name': product.name,
            'price': product.price,
            'category': product.category,
            'description': product.description,
            'image': '/static/' + product.image,
            'status': product.status,
            'seller_id': int(product.seller_id)
        })

    return jsonify(product_list)

@app.route('/all_sellers')
@login_required
def all_sellers():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can view sellers'}), 403

    sellers = User.query.filter_by(role='seller').all()
    seller_list = []
    for seller in sellers:
        seller_list.append({
            'id': int(seller.id),
            'name': seller.name,
            'email': seller.email
        })

    return jsonify(seller_list)

@app.route('/all_buyers')
@login_required
def all_buyers():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can view buyers'}), 403

    buyers = User.query.filter_by(role='buyer').all()
    buyer_list = []
    for buyer in buyers:
        buyer_list.append({
            'id': int(buyer.id),
            'name': buyer.name,
            'email': buyer.email,
            'join_date': buyer.orders[0].order_date.isoformat() if buyer.orders else 'N/A' # Example data
        })

    return jsonify(buyer_list)

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@login_required
def admin_delete_product(product_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Only admins can delete products'}), 403

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    # Delete image file if it exists
    if product.image:
        image_path = os.path.join(app.root_path, 'static', product.image)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass  # Ignore if file deletion fails

    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Product removed successfully by admin'})

@app.route('/api/admin/feedback')
@login_required
def get_admin_feedback():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    feedback_list = []
    for f in feedbacks:
        feedback_list.append({
            'id': f.id,
            'user_name': f.user.name,
            'user_role': f.user_role,
            'rating': f.rating,
            'feedback_text': f.feedback_text,
            'timestamp': f.timestamp.isoformat(),
            'admin_reply': f.admin_reply,
            'replied_at': f.replied_at.isoformat() if f.replied_at else None
        })

    return jsonify(feedback_list)

@app.route('/api/admin/feedback/reply/<int:feedback_id>', methods=['POST'])
@login_required
def reply_to_feedback(feedback_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    reply_text = data.get('reply_text')
    if not reply_text:
        return jsonify({'success': False, 'message': 'Reply text is required.'}), 400

    feedback_item = db.session.get(Feedback, feedback_id)
    if not feedback_item:
        return jsonify({'success': False, 'message': 'Feedback not found.'}), 404

    feedback_item.admin_reply = reply_text
    feedback_item.replied_at = datetime.now(timezone.utc)
    db.session.commit()

    # Notify the user about the reply
    create_and_send_notification(
        user_id=feedback_item.user_id,
        title='Admin Replied to Your Feedback',
        message=f"An admin has replied to your feedback: '{reply_text[:50]}...'",
        redirect_url=url_for('feedback')
    )

    return jsonify({'success': True, 'message': 'Reply sent successfully.'})

# Cart API routes
@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can add to cart'}), 403

    data = request.get_json()
    product_id = int(data.get('product_id'))
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400

    product = db.session.get(Product, product_id)
    if not product or product.status != 'approved':
        return jsonify({'success': False, 'message': 'Product not available'}), 404

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Added to cart'})

@app.route('/api/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can remove from cart'}), 403

    data = request.get_json()
    product_id = int(data.get('product_id'))

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return jsonify({'success': False, 'message': 'Cart not found'}), 404

    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Item not in cart'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Removed from cart'})

@app.route('/api/cart/update', methods=['POST'])
@login_required
def update_cart():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can update cart'}), 403

    data = request.get_json()
    product_id = int(data.get('product_id'))
    quantity = data.get('quantity', 0)

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return jsonify({'success': False, 'message': 'Cart not found'}), 404

    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Item not in cart'}), 404

    if quantity > 0:
        item.quantity = quantity
    else:
        db.session.delete(item)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Cart updated'})

@app.route('/api/cart/get')
@login_required
def get_cart():
    if current_user.role != 'buyer':
        return jsonify({'message': 'Only logged-in users can view cart'}), 403

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        return jsonify([])

    items = []
    for item in cart.items:
        items.append({
            'id': int(item.product.id),
            'name': item.product.name,
            'price': item.product.price,
            'image': '/static/' + item.product.image,
            'category': item.product.category,
            'qty': item.quantity
        })

    return jsonify(items)

# Wishlist API routes
@app.route('/api/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can add to wishlist'}), 403

    data = request.get_json()
    product_id = int(data.get('product_id'))

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400

    product = db.session.get(Product, product_id)
    if not product or product.status != 'approved':
        return jsonify({'success': False, 'message': 'Product not available'}), 404

    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id)
        db.session.add(wishlist)
        db.session.commit()

    item = WishlistItem.query.filter_by(wishlist_id=wishlist.id, product_id=product_id).first()
    if not item:
        item = WishlistItem(wishlist_id=wishlist.id, product_id=product_id)
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    else:
        return jsonify({'success': False, 'message': 'Already in wishlist'})

@app.route('/api/wishlist/remove', methods=['POST'])
@login_required
def remove_from_wishlist():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can remove from wishlist'}), 403

    data = request.get_json()
    product_id = int(data.get('product_id'))

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400

    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        return jsonify({'success': False, 'message': 'Wishlist not found'}), 404

    item = WishlistItem.query.filter_by(wishlist_id=wishlist.id, product_id=product_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Item not in wishlist'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Removed from wishlist'})

@app.route('/api/wishlist/get')
@login_required
def get_wishlist():
    if current_user.role != 'buyer':
        return jsonify({'message': 'Only logged-in users can view wishlist'}), 403

    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        return jsonify([])

    items = []
    for item in wishlist.items:
        items.append({
            'id': int(item.product.id),
            'name': item.product.name,
            'price': item.product.price,
            'image': '/static/' + item.product.image,
            'category': item.product.category
        })

    return jsonify(items)



@app.route('/my_orders')
@login_required
def my_orders():
    orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status != 'Pending Payment'
    ).order_by(Order.order_date.desc()).all()
    return render_template('my-orders.html', orders=orders)

@app.route('/invoice/<int:order_id>')
@login_required
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'message': 'You are not authorized to view this invoice'}), 403

    if order.payment_method == 'upi' and order.invoice_generated:
        return render_template('invoice.html', order=order)
    else:
        return jsonify({'message': 'Invoice not available'}), 404

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('fullname')
        current_user.address = request.form.get('address')
        password = request.form.get('password')
        if password:
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')


@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Soft-delete the current user's account.
    Sets `is_deleted` and `deleted_at`, anonymizes identifying fields, and
    marks seller products as removed. Prevents deleting admin accounts.
    """
    import time

    user_id = current_user.id
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    # Prevent deleting admin accounts via this route
    if user.role == 'admin':
        return jsonify({'success': False, 'message': 'Admin accounts cannot be deleted via this page.'}), 403

    # If seller, ensure no order items exist referencing their products
    if user.role == 'seller':
        linked_orderitem = db.session.query(OrderItem).join(Product, Product.id == OrderItem.product_id).filter(Product.seller_id == user_id).first()
        if linked_orderitem:
            return jsonify({'success': False, 'message': 'Cannot delete seller account while orders exist for your products. Please resolve orders first.'}), 400

        # Mark products as removed (so they no longer appear in listings)
        products = Product.query.filter_by(seller_id=user_id).all()
        for p in products:
            p.status = 'removed'

    # Anonymize user fields and mark soft-deleted
    try:
        timestamp = int(time.time())
        user.name = 'Deleted User'
        # Make email unique by appending a deleted suffix
        user.email = f"deleted_{user.id}_{timestamp}_{user.email}"
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to soft-delete account: ' + str(e)}), 500

    # Log out the user and redirect to home
    try:
        logout_user()
    except Exception:
        pass

    return jsonify({'success': True, 'redirect': url_for('index')})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('New passwords do not match!', 'error')
            return render_template('forgot-password.html')

        user = User.query.filter_by(email=email).first()
        if user:
            user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            flash('Password reset successfully! Please log in with your new password.', 'success')
            return redirect(url_for('index'))
        else:
            flash('No user found with that email.', 'error')
            return render_template('forgot-password.html')

    return render_template('forgot-password.html')

# ===================================
# NOTIFICATION API ROUTES
# ===================================
@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'timestamp': n.timestamp.isoformat(),
        'type': n.type,
        'redirect_url': n.redirect_url
    } for n in notifications])

@app.route('/api/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/read/all', methods=['POST'])
@login_required
def mark_all_as_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    db.session.delete(notification)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/payment/initiate', methods=['POST'])
@login_required
def initiate_payment():
    """Creates an order with a 'Pending Payment' status and a corresponding payment record."""
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        return jsonify({'message': 'Your cart is empty'}), 400

    if not current_user.address:
        return jsonify({'message': 'Please add a shipping address to your profile before placing an order.'}), 400

    total_price = sum(item.product.price * item.quantity for item in cart.items)

    # Create the order first with a pending status
    new_order = Order(
        user_id=current_user.id,
        total_price=total_price,
        payment_method='upi',
        shipping_address=current_user.address,
        status='Pending Payment', # New initial status
        estimated_delivery_date=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.session.add(new_order)
    db.session.commit()

    # Create the payment record
    new_payment = Payment(
        order_id=new_order.id,
        amount=total_price,
        payment_method='upi',
        status='pending'
    )
    db.session.add(new_payment)
    db.session.commit()

    return jsonify({'success': True, 'order_id': new_order.id, 'total_amount': total_price})

@app.route('/api/payment/confirm/<int:order_id>', methods=['POST'])
@login_required
def confirm_payment(order_id):
    """Confirms a payment after the user clicks 'I Have Paid'."""
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'message': 'Order not found or unauthorized.'}), 404

    # Update Order
    order.status = 'Paid'
    order.invoice_generated = True

    # Update Payment
    payment = order.payment
    if payment:
        payment.status = 'completed'
        payment.payment_date = datetime.now(timezone.utc)
    
    # The rest of the order processing (stock, notifications) happens in place_order
    # We will call place_order logic from here.
    with app.test_request_context(
        '/place_order', method='POST',
        json={'from_confirmation': True, 'order_id': order.id}
    ):
        return place_order()

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    # This is a simplified order placement route for demonstration
    data = request.get_json()
    payment_method = data.get('payment_method', 'cod')
    payment_details = data.get('payment_details')

    # This function can now be called from two places.
    # 1. Directly for COD orders.
    # 2. From confirm_payment for UPI orders.
    from_confirmation = request.json.get('from_confirmation', False)

    shipping_address = current_user.address
    if not shipping_address:
        return jsonify({'message': 'Please add a shipping address to your profile before placing an order.'}), 400

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        return jsonify({'message': 'Your cart is empty.'}), 400

    total_price = sum(item.product.price * item.quantity for item in cart.items)

    # If it's a UPI confirmation, fetch the existing order. Otherwise, create a new one for COD.
    if from_confirmation:
        order_id = request.json.get('order_id')
        new_order = db.session.get(Order, order_id)
    elif payment_method == 'cod':
        new_order = Order(
            user_id=current_user.id,
            total_price=total_price,
            payment_method='cod',
            shipping_address=shipping_address,
            status='Processing',
            estimated_delivery_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.session.add(new_order)
        db.session.commit()

        new_payment = Payment(
            order_id=new_order.id,
            amount=total_price,
            payment_method='cod',
            status='pending'
        )
        db.session.add(new_payment)
    else:
        # This case should not be reached in the current flow, but it's good practice to handle it.
        return jsonify({'message': 'Invalid payment method for this endpoint.'}), 400

    for item in cart.items:
        # Add item to order
        order_item = OrderItem(order=new_order, product_id=item.product_id, quantity=item.quantity, price=item.product.price)
        db.session.add(order_item)

        # Notify seller
        seller_id = item.product.seller_id
        create_and_send_notification(
            user_id=seller_id,
            title='Product Sold!',
            message=f"You sold {item.quantity}x of '{item.product.name}'. Order #{new_order.id}.",
            redirect_url=url_for('seller_dashboard') + '#seller-orders'
        )

        # Update stock
        item.product.stock -= item.quantity
        if item.product.stock <= 5 and item.product.stock > 0: # Low stock warning
            create_and_send_notification(
                user_id=seller_id,
                title='Low Stock Warning',
                message=f"Stock for '{item.product.name}' is low ({item.product.stock} left).",
                redirect_url=url_for('seller_dashboard') + '#my-products'
            )

    db.session.query(CartItem).filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return jsonify({'message': 'Order placed successfully!', 'order_id': new_order.id})

@app.route('/api/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    if current_user.role != 'buyer': # This check is already good!
        return jsonify({'success': False, 'message': 'Only buyers can cancel orders.'}), 403

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'You are not authorized to cancel this order.'}), 403

    if order.status != 'Processing':
        return jsonify({'success': False, 'message': f"Order cannot be cancelled as it is already '{order.status}'."}), 400

    order.status = 'Cancelled'
    db.session.commit()

    # Notify all sellers in the order
    seller_ids = {item.product.seller_id for item in order.items}
    for seller_id in seller_ids:
        create_and_send_notification(
            user_id=seller_id,
            title='Order Cancelled',
            message=f"Order #{order.id} has been cancelled by the buyer.",
            redirect_url=url_for('seller_dashboard') + '#seller-orders'
        )

    return jsonify({'success': True, 'message': 'Order has been successfully cancelled.'})

# ===================================
# REVIEW API ROUTES
# ===================================
@app.route('/api/product/<int:product_id>/reviews', methods=['GET'])
def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.timestamp.desc()).all()
    review_list = []
    for review in reviews:
        review_list.append({
            'id': review.id,
            'rating': review.rating,
            'text': review.text,
            'timestamp': review.timestamp.isoformat(),
            'user': {
                'name': review.user.name
            }
        })
    return jsonify(review_list)

@app.route('/api/product/<int:product_id>/review', methods=['POST'])
@login_required
def post_review(product_id):
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can post reviews.'}), 403

    data = request.get_json()
    rating = data.get('rating')
    text = data.get('text')

    if not rating or not text:
        return jsonify({'success': False, 'message': 'Rating and review text are required.'}), 400

    new_review = Review(
        product_id=product_id,
        user_id=current_user.id,
        rating=int(rating),
        text=text
    )
    db.session.add(new_review)
    db.session.commit()

    # Broadcast the new review to all clients
    payload = {
        'rating': new_review.rating, 'text': new_review.text, 'user': {'name': current_user.name}
    }
    socketio.emit('new_review', {'product_id': product_id, 'review': payload})

    return jsonify({'success': True, 'message': 'Review submitted successfully.'}), 201


# ===================================
# CHAT API ROUTES
# ===================================

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user."""
    conversations = Conversation.query.filter(
        or_(Conversation.buyer_id == current_user.id, Conversation.seller_id == current_user.id)
    ).order_by(Conversation.id.desc()).all()

    conv_list = []
    for conv in conversations:
        other_user = conv.seller if conv.buyer_id == current_user.id else conv.buyer
        last_message = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp.desc()).first()
        unread_count = Message.query.filter_by(conversation_id=conv.id, receiver_id=current_user.id, is_read=False).count()

        conv_list.append({
            'id': conv.id,
            'product_id': conv.product_id,
            'product_name': conv.product.name,
            'other_user_id': other_user.id,
            'other_user_name': other_user.name,
            'last_message_content': last_message.content if last_message else 'No messages yet.',
                'last_message_timestamp': last_message.timestamp.isoformat() if last_message else None,
                'last_message_timestamp_ms': int(last_message.timestamp.timestamp() * 1000) if last_message else None,
            'unread_count': unread_count
        })
    return jsonify(conv_list)

@app.route('/api/conversations/start', methods=['POST'])
@login_required
def start_conversation():
    """Start a new conversation or retrieve an existing one."""
    data = request.get_json()
    product_id = data.get('product_id')
    seller_id = data.get('seller_id')

    if not product_id or not seller_id:
        return jsonify({'success': False, 'message': 'Product ID and Seller ID are required.'}), 400

    if current_user.id == int(seller_id):
        return jsonify({'success': False, 'message': 'You cannot start a chat with yourself.'}), 400

    # Check if a conversation already exists for this buyer, seller, and product
    conversation = Conversation.query.filter_by(
        buyer_id=current_user.id,
        seller_id=seller_id,
        product_id=product_id
    ).first()

    if not conversation:
        product = db.session.get(Product, product_id)
        if not product:
             return jsonify({'success': False, 'message': 'Product not found.'}), 404

        conversation = Conversation(
            buyer_id=current_user.id,
            seller_id=seller_id,
            product_id=product_id
        )
        db.session.add(conversation)
        db.session.commit()

        # Notify the seller about the new conversation
        create_and_send_notification(
            user_id=seller_id,
            title='New Conversation Started',
            message=f"You have a new message from {current_user.name} regarding '{product.name}'.",
            redirect_url=url_for('chat_page', conversation_id=conversation.id)
        )

    return jsonify({'success': True, 'conversation_id': conversation.id})

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@login_required
def get_messages(conversation_id):
    """Get messages for a specific conversation."""
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        return jsonify({'success': False, 'message': 'Conversation not found or unauthorized.'}), 404

    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp.asc()).all()
    message_list = []
    for msg in messages:
        # Treat naive datetime as UTC (MySQL stores as naive but we save UTC)
        msg_ts = msg.timestamp
        if msg_ts.tzinfo is None:
            msg_ts = msg_ts.replace(tzinfo=timezone.utc)
        ts_ms = int(msg_ts.timestamp() * 1000)
        message_list.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.name,
            'receiver_id': msg.receiver_id,
            'receiver_name': msg.receiver.name,
            'content': msg.content,
            'timestamp': msg_ts.isoformat(),
            'timestamp_ms': ts_ms,
            'is_read': msg.is_read
        })
    
    # Debug: log timestamps returned by the API for inspection
    try:
        for m in message_list:
            logger.debug(f"API message id={m['id']} iso={m['timestamp']} ms={m['timestamp_ms']}")
    except Exception:
        pass

    return jsonify(message_list)

@app.route('/api/conversations/<int:conversation_id>/read', methods=['POST'])
@login_required
def mark_conversation_as_read(conversation_id):
    """Mark all unread messages in a conversation as read for the current user."""
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        return jsonify({'success': False, 'message': 'Conversation not found or unauthorized.'}), 404

    messages_to_update = Message.query.filter_by(
        conversation_id=conversation_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()

    for msg in messages_to_update:
        msg.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'message': f'{len(messages_to_update)} messages marked as read.'})

@socketio.on('join_conversation')
def on_join(data):
    conversation_id = data['conversation_id']
    join_room(f'conversation_{conversation_id}')

@socketio.on('leave_conversation')
def on_leave(data):
    conversation_id = data['conversation_id']
    # Leaving rooms happens automatically on disconnect, but this is good practice if a user navigates away
    from flask_socketio import leave_room
    leave_room(f'conversation_{conversation_id}')

@socketio.on('send_message')
@login_required
def handle_send_message(data):
    conversation_id = data['conversation_id']
    content = data['content']
    temp_id = data.get('temp_id') if isinstance(data, dict) else None

    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        return # Or emit an error

    receiver_id = conversation.seller_id if current_user.id == conversation.buyer_id else conversation.buyer_id

    new_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()

    # Treat naive timestamp as UTC before converting to epoch
    msg_ts = new_message.timestamp
    if msg_ts.tzinfo is None:
        msg_ts = msg_ts.replace(tzinfo=timezone.utc)
    ts_ms = int(msg_ts.timestamp() * 1000)
    
    message_payload = {
        'id': new_message.id,
        'sender_id': new_message.sender_id,
        'sender_name': current_user.name,
        'receiver_id': receiver_id,
        'receiver_name': new_message.receiver.name,
        'content': new_message.content,
        'timestamp': msg_ts.isoformat(),
        'timestamp_ms': ts_ms,
        'temp_id': temp_id,
        'is_read': new_message.is_read
    }

    # Debug: log the timestamp values being saved/emitted
    try:
        logger.debug(f"New message saved id={new_message.id} iso={msg_ts.isoformat()} ms={ts_ms}")
    except Exception as e:
        print("[DEBUG] Failed to log message timestamp:", e)

    # Emit the message to the specific conversation room
    emit('new_message', message_payload, room=f'conversation_{conversation_id}')

    # Send a general notification to the receiver's user room
    create_and_send_notification(
        user_id=receiver_id,
        title=f"New Message from {current_user.name}",
        message=content[:50] + '...', # Truncate message for notification
        redirect_url=url_for('chat_page', conversation_id=conversation_id)
    )

@app.route('/chat-histories')
@login_required
def chat_histories():
    return render_template('chat-histories.html')


# ===================================
# ADMIN REPORTING API ROUTES
# ===================================

@app.route('/api/reports/monthly-sales')
@login_required
def monthly_sales_report():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    sales_data = db.session.query(
        extract('year', Order.order_date).label('year'),
        extract('month', Order.order_date).label('month'),
        func.sum(Order.total_price).label('total_sales')
    ).filter(Order.status != 'Cancelled').group_by('year', 'month').order_by('year', 'month').all()

    report = [{'month': f"{int(s.year)}-{int(s.month):02d}", 'sales': s.total_sales} for s in sales_data]
    return jsonify(report)

@app.route('/api/reports/product-performance')
@login_required
def product_performance_report():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    product_data = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('units_sold'),
        func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue')
    ).join(OrderItem, Product.id == OrderItem.product_id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .filter(Order.status != 'Cancelled')\
     .group_by(Product.name)\
     .order_by(func.sum(OrderItem.quantity).desc()).all()

    report = [{'product_name': p.name, 'units_sold': p.units_sold, 'total_revenue': p.total_revenue} for p in product_data]
    return jsonify(report)

@app.route('/api/reports/daily-sales')
@login_required
def daily_sales_report():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = db.session.query(
        func.date(Order.order_date).label('date'),
        func.sum(Order.total_price).label('total_sales')
    ).filter(Order.status != 'Cancelled')

    if start_date_str and end_date_str:
        try:
            # Parse date strings and make them timezone-aware for correct filtering
            start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
            # Add one day to the end date to make the range inclusive
            end_date = (datetime.fromisoformat(end_date_str) + timedelta(days=1)).replace(tzinfo=timezone.utc)
            query = query.filter(Order.order_date >= start_date, Order.order_date < end_date)
        except ValueError:
            # Fallback to default if date format is incorrect
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.filter(Order.order_date >= thirty_days_ago)
    else:
        # Default to the last 30 days if no dates are provided
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(Order.order_date >= thirty_days_ago)

    sales_data = query.group_by(func.date(Order.order_date)).order_by(func.date(Order.order_date).asc()).all()

    report = [{'date': s.date.isoformat(), 'sales': s.total_sales} for s in sales_data]
    return jsonify(report)

@app.route('/api/reports/payment-details')
@login_required
def payment_details_report():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    payments = Payment.query.order_by(Payment.id.desc()).all()
    report = [{
        'payment_id': p.id,
        'order_id': p.order_id,
        'user_name': p.order.user.name,
        'amount': p.amount,
        'payment_method': p.payment_method,
        'status': p.status,
        'payment_date': p.payment_date.isoformat() if p.payment_date else 'N/A'
    } for p in payments]
    return jsonify(report)

@app.route('/api/reports/dashboard-overview')
@login_required
def dashboard_overview_report():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    # 1. Real-Time Overview Metrics
    total_sales = db.session.query(func.sum(Order.total_price)).filter(Order.status != 'Cancelled').scalar() or 0
    total_orders = db.session.query(func.count(Order.id)).scalar() or 0
    active_listings = db.session.query(func.count(Product.id)).filter_by(status='approved').scalar() or 0
    total_sellers = db.session.query(func.count(User.id)).filter_by(role='seller').scalar() or 0
    total_buyers = db.session.query(func.count(User.id)).filter_by(role='buyer').scalar() or 0

    # 2. Customer Behaviour Metrics
    avg_order_value = db.session.query(func.avg(Order.total_price)).filter(Order.status != 'Cancelled').scalar() or 0

    peak_hours_data = db.session.query(
        extract('hour', Order.order_date).label('hour'),
        func.count(Order.id).label('order_count')
    ).group_by('hour').order_by('hour').all()
    peak_purchasing_times = [{'hour': h.hour, 'orders': h.order_count} for h in peak_hours_data]

    # 3. Performance Tracking
    seller_ratings_data = db.session.query(
        User.name,
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).join(Product, User.id == Product.seller_id)\
     .join(Review, Product.id == Review.product_id)\
     .group_by(User.id)\
     .order_by(func.avg(Review.rating).desc())\
     .limit(10).all() # Top 10 sellers
    seller_performance = [{'seller_name': s.name, 'avg_rating': float(s.avg_rating)} for s in seller_ratings_data]

    # 4. University Commerce Overview
    platform_growth_data = db.session.query(
        extract('year', User.date_joined).label('year'),
        extract('month', User.date_joined).label('month'),
        func.count(User.id).label('new_users')
    ).group_by('year', 'month').order_by('year', 'month').all()
    platform_growth = [{'period': f"{int(g.year)}-{int(g.month):02d}", 'new_users': g.new_users} for g in platform_growth_data]

    overview_data = {
        'overview_metrics': {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'active_listings': active_listings,
            'total_sellers': total_sellers,
            'total_buyers': total_buyers,
            'average_order_value': avg_order_value
        },
        'customer_behaviour': {
            'peak_purchasing_times': peak_purchasing_times
        },
        'performance_tracking': {
            'seller_performance': seller_performance
        },
        'platform_growth': {
            'monthly_new_users': platform_growth
        }
    }
    return jsonify(overview_data)


@app.route('/api/seller/revenue')
@login_required
def seller_revenue():
    """Return seller's total revenue and recent monthly breakdown (last 6 months)."""
    # Only sellers should access this
    if current_user.role != 'seller':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # Total revenue for this seller: sum of price * quantity for items sold where order not cancelled
    total_revenue = (
        db.session.query(func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0))
        .join(Product, Product.id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Product.seller_id == current_user.id, Order.status != 'Cancelled')
        .scalar()
    )

    if total_revenue is None:
        total_revenue = 0

    # Monthly breakdown (last 6 months)
    from datetime import datetime
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        m = (now.month - i - 1) % 12 + 1
        y = (now.year + ((now.month - i - 1) // 12))
        months.append((y, m))

    monthly_query = (
        db.session.query(
            extract('year', Order.order_date).label('year'),
            extract('month', Order.order_date).label('month'),
            func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0).label('revenue')
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Product.seller_id == current_user.id, Order.status != 'Cancelled')
        .group_by('year', 'month')
        .order_by('year', 'month')
    )

    results = monthly_query.all()
    # Map results to dict keyed by (year, month)
    res_map = {(int(r.year), int(r.month)): float(r.revenue or 0) for r in results}

    labels = []
    values = []
    for y, m in months:
        labels.append(f"{y}-{m:02d}")
        values.append(res_map.get((y, m), 0))

    return jsonify({'success': True, 'total_revenue': float(total_revenue), 'monthly_labels': labels, 'monthly_values': values})

   

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    with app.app_context():
        db.create_all()

    # Pass port through to Flask-SocketIO/Flask dev server
    socketio.run(app, debug=True, port=args.port)
