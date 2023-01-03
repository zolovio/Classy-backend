import os
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from project.api.authentications import authenticate
from project.exceptions import APIError
from project.api.validators import field_type_validator, required_validator

from project.models import (
    User,
    Location,
    ShoppingCart,
    CartItem,
    Sku,
    Sku_Stock,
    Campaign,
    Coupon,
    Order,
    Order_Sku
)

shopping_blueprint = Blueprint(
    'shopping', __name__, template_folder='./templates')

logger = logging.getLogger(__name__)


@shopping_blueprint.route('/shopping/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@shopping_blueprint.route('/shopping/get_cart', methods=['GET'])
@authenticate
def get_cart(user_id):
    """Get cart"""

    shopping_cart = ShoppingCart.query.filter_by(
        user_id=user_id, is_active=True).first()

    if not shopping_cart:

        # create a new cart
        shopping_cart = ShoppingCart(user_id=user_id)
        shopping_cart.insert()

        logger.info('New cart created for user: {}'.format(user_id))

    logger.info('Cart id: {}'.format(shopping_cart.id))
    cart_items = CartItem.query.filter_by(cart_id=shopping_cart.id).all()

    total_amount = 0
    for cart_item in cart_items:
        campaign = Campaign.query.get(cart_item.campaign_id)
        sku = Sku.query.get(campaign.sku_id)

        total_amount += (sku.price * cart_item.quantity)

    response_object = {
        'status': True,
        'message': '{} item(s) found in cart'.format(len(cart_items)),
        'data': {
            'cart': [cart_item.to_json() for cart_item in cart_items],
            'total_amount': round(total_amount, 2)
        }
    }

    return jsonify(response_object), 200


@shopping_blueprint.route('/shopping/add_to_cart', methods=['POST'])
@authenticate
def add_to_cart(user_id):
    """Add item to cart"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    post_data = request.get_json()

    field_types = {'campaign_id': int, 'sku_images_id': int,
                   'sku_stock_id': int, 'quantity': int}

    required_fields = list(field_types.keys())

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    campaign_id = post_data.get('campaign_id')
    sku_images_id = post_data.get('sku_images_id')
    sku_stock_id = post_data.get('sku_stock_id')
    quantity = post_data.get('quantity')

    # check if campaign exists
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    if not campaign:
        response_object['message'] = 'Campaign does not exist'
        return jsonify(response_object), 200

    sku = Sku.query.get(campaign.sku_id)
    if not sku:
        response_object['message'] = 'SKU does not exist'
        return jsonify(response_object), 200

    # check available stock
    sku_stock = Sku_Stock.query.get(sku_stock_id)
    if not sku_stock:
        response_object['message'] = 'Stock does not exist'
        return jsonify(response_object), 200

    # check if user has already added this item to cart
    shopping_cart = ShoppingCart.query.filter_by(
        user_id=user_id, is_active=True).first()

    if not shopping_cart:
        # create a new cart
        shopping_cart = ShoppingCart(user_id=user_id)
        shopping_cart.insert()

        logger.info('New cart created for user: {}'.format(user_id))

    else:
        cart_item = CartItem.query.filter_by(
            cart_id=shopping_cart.id, sku_stock_id=sku_stock_id).first()

        if cart_item:
            response_object['message'] = 'Item already in cart, please update quantity instead'
            return jsonify(response_object), 200

    if sku_stock.stock < quantity:
        response_object['message'] = 'Not enough stock'
        return jsonify(response_object), 200

    # add item to cart
    cart_item = CartItem(
        cart_id=shopping_cart.id,
        campaign_id=campaign_id,
        sku_stock_id=sku_stock_id,
        sku_images_id=sku_images_id,
        quantity=quantity
    )

    cart_item.insert()

    # update stock
    sku_stock.stock -= quantity
    sku_stock.update()

    response_object['status'] = True
    response_object['message'] = 'Item added to cart'
    response_object['id'] = cart_item.id

    return jsonify(response_object), 200


@shopping_blueprint.route('/shopping/update_cart/<int:cart_item_id>', methods=['PUT'])
@authenticate
def update_cart(user_id, cart_item_id):
    """Update item in cart"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    post_data = request.get_json()

    field_types = {'quantity': int}

    required_fields = list(field_types.keys())

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    quantity = post_data.get('quantity')

    # check if cart exists
    shopping_cart = ShoppingCart.query.filter_by(user_id=user_id).first()
    if not shopping_cart:
        response_object['message'] = 'Cart does not exist'
        return jsonify(response_object), 200

    cart_item = CartItem.query.get(cart_item_id)
    # check if cart item exists
    if not cart_item:
        response_object['message'] = 'Cart item does not exist'
        return jsonify(response_object), 200

    sku_stock = Sku_Stock.query.get(cart_item.sku_stock_id)
    # check available stock
    if not sku_stock:
        response_object['message'] = 'Stock does not exist'
        return jsonify(response_object), 200

    sku = Sku.query.get(sku_stock.sku_id)
    if not shopping_cart.is_active:
        response_object['message'] = 'Cart containing item {} already checked out'.format(
            sku.name)
        return jsonify(response_object), 200

    if quantity < cart_item.quantity:
        # add stock
        sku_stock.stock += (cart_item.quantity - quantity)

    elif quantity > cart_item.quantity:
        if sku_stock.stock <= (quantity - cart_item.quantity):
            response_object['message'] = 'Not enough stock'
            return jsonify(response_object), 200

        # remove stock
        sku_stock.stock -= (quantity - cart_item.quantity)

    # update or remove cart item
    if quantity == 0:
        cart_item.delete()

    else:
        cart_item.quantity = quantity
        cart_item.update()

    # update stock
    sku_stock.update()

    response_object['status'] = True
    response_object['message'] = 'Cart item updated'

    return jsonify(response_object), 200


@shopping_blueprint.route('/shopping/remove_from_cart/<int:cart_item_id>', methods=['DELETE'])
@authenticate
def remove_from_cart(user_id, cart_item_id):
    """Remove item from cart"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    # check if cart item exists
    cart_item = CartItem.query.get(cart_item_id)
    if not cart_item:
        response_object['message'] = 'Cart item does not exist'
        return jsonify(response_object), 200

    # check available stock
    sku_stock = Sku_Stock.query.get(cart_item.sku_stock_id)
    if not sku_stock:
        response_object['message'] = 'Cart item does not match any stock'
        return jsonify(response_object), 200

    # update stock
    sku_stock.stock += cart_item.quantity
    sku_stock.update()

    # remove cart item
    cart_item.delete()

    response_object['status'] = True
    response_object['message'] = 'Cart item removed'

    return jsonify(response_object), 200


@shopping_blueprint.route('/shopping/checkout', methods=['GET'])
@authenticate
def checkout(user_id):
    """Checkout cart"""
    # Make user cart inactive and add checkedout date to cart
    response_object = {
        'status': True,
        'message': 'Invalid payload.'
    }

    # check if cart exists
    shopping_cart = ShoppingCart.query.filter_by(
        user_id=user_id, is_active=True).first()

    if not shopping_cart:
        response_object['message'] = 'Cart does not exist'
        return jsonify(response_object), 200

    # check if cart is already checked out
    if shopping_cart.checkedout_at:
        response_object['message'] = 'Cart already checked out'
        return jsonify(response_object), 200

    # check if cart is empty
    cart_items = CartItem.query.filter_by(cart_id=shopping_cart.id).all()
    if not cart_items:
        response_object['message'] = 'Cart is empty, please add item(s) to cart'
        return jsonify(response_object), 200

    shopping_cart.checkedout_at = datetime.utcnow()
    shopping_cart.update()

    response_object['status'] = True
    response_object['message'] = 'Cart checked out at {}'.format(
        shopping_cart.checkedout_at.strftime('%Y-%m-%d %H:%M:%S'))

    return jsonify(response_object), 200
