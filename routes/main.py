from flask import Blueprint, render_template, request
from sqlalchemy import or_
from database import Product

main_bp = Blueprint('main', __name__)

@main_bp.route('/category/<string:category_name>')
def category(category_name):
    products = Product.query.filter_by(category=category_name, status='approved').all()
    return render_template('category.html', products=products, category_title=category_name)

@main_bp.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@main_bp.route('/clothes')
def clothes():
    return render_template('clothes.html')

@main_bp.route('/baked-goods')
def baked_goods():
    return render_template('baked-goods.html')

@main_bp.route('/jewellery')
def jewellery():
    return render_template('jewellery.html')

@main_bp.route('/paintings')
def paintings():
    return render_template('paintings.html')

@main_bp.route('/cart')
def cart():
    return render_template('cart.html')

@main_bp.route('/checkout')
def checkout():
    return render_template('checkout.html')

@main_bp.route('/wishlist')
def wishlist():
    return render_template('wishlist.html')

@main_bp.route('/notifications')
def notifications():
    return render_template('notifications.html')

@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search_results.html', products=[], query=query)

    search_term = f'%{query}%'
    products = Product.query.filter(
        or_(
            Product.name.like(search_term),
            Product.description.like(search_term),
            Product.category.like(search_term)
        ),
        Product.status == 'approved'
    ).all()

    return render_template('search_results.html', products=products, query=query)
