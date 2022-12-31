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

order_blueprint = Blueprint('order', __name__, template_folder='templates')

logger = logging.getLogger(__name__)

ORDER_STATUS_LIST = ['pending', 'paid', 'shipped',
                     'delivered', 'cancelled', 'exchanged', 'returned']


@order_blueprint.route('/order/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong V0.1!'
    })


@order_blueprint.route('/order/create', methods=['POST'])
@authenticate
def create_order(user_id):
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    """Create order"""
    post_data = request.get_json()
    field_types = {'shipping_fee': float, 'location_id': int}

    required_fields = list(field_types.keys())
    required_fields.remove('location_id')

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    shipping_fee = post_data.get('shipping_fee')
    location_id = post_data.get('location_id')

    if not location_id:
        location_id = Location.query.filter_by(user_id=user_id).first().id

    shopping_cart = ShoppingCart.query.filter_by(user_id=user_id).first()
    if not shopping_cart:
        response_object['message'] = 'Cart does not exist'
        return jsonify(response_object), 404

    if shopping_cart.user_id != user_id:
        response_object['message'] = 'Cart does not belong to user'
        return jsonify(response_object), 401

    if not shopping_cart.is_active:
        response_object['message'] = 'Cart is already processed'
        return jsonify(response_object), 400

    if not shopping_cart.checked_out:
        response_object['message'] = 'Cart is not checked out yet'
        return jsonify(response_object), 400

    order = Order(
        user_id=user_id,
        location_id=location_id,
        total_quantity=0,
        total_tax=0,
        total_amount=0,
        shipping_fee=shipping_fee,
        booking_date=datetime.utcnow()
    )

    order.insert()

    cart_items = CartItem.query.filter_by(cart_id=shopping_cart.id).all()
    for cart_item in cart_items:
        campaign = Campaign.query.get(cart_item.campaign_id)
        sku = Sku.query.get(campaign.sku_id)

        # create coupon
        coupon = Coupon(
            user_id=user_id,
            campaign_id=campaign.id,
            sku_images_id=cart_item.sku_images_id,
            sku_stock_id=cart_item.sku_stock_id,
            datetime=datetime.utcnow(),
            amount_paid=(sku.price * cart_item.quantity),
        )

        coupon.insert()

        # create order item
        order_sku = Order_Sku(
            order_id=order.id,
            quantity=cart_item.quantity,
            total_price=sku.price * cart_item.quantity,
            sales_tax=sku.sales_tax,
            coupon_id=coupon.id,
            campaign_id=cart_item.campaign_id,
            sku_images_id=cart_item.sku_images_id,
            sku_stock_id=cart_item.sku_stock_id,
        )

        order_sku.insert()

        # update sku
        sku.quantity -= order_sku.quantity
        sku.number_sold += order_sku.quantity
        sku.update()

        # update order
        order.total_quantity += order_sku.quantity
        order.total_amount += order_sku.total_price
        order.total_tax += order_sku.sales_tax
        order.update()

    # update cart
    shopping_cart.is_active = False
    shopping_cart.update()

    response_object['status'] = 'success'
    response_object['message'] = 'Order created successfully'
    response_object['data'] = {
        'order': order.to_json()
    }

    return jsonify(response_object), 201


@order_blueprint.route('/order/update/<int:order_id>', methods=['PATCH'])
@authenticate
def update_order(user_id, order_id):
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    """Update order"""
    post_data = request.get_json()
    field_types = {'shipping_fee': float, 'location_id': int}

    required_fields = list(field_types.keys())
    required_fields.remove('location_id')

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    shipping_fee = post_data.get('shipping_fee')
    location_id = post_data.get('location_id')

    if not location_id:
        location_id = Location.query.filter_by(user_id=user_id).first().id

    order = Order.query.get(order_id)
    if not order:
        response_object['message'] = 'Order does not exist'
        return jsonify(response_object), 404

    if order.user_id != user_id:
        response_object['message'] = 'Order does not belong to user'
        return jsonify(response_object), 401

    order.shipping_fee = shipping_fee
    order.location_id = location_id
    order.update()

    response_object['status'] = 'success'
    response_object['message'] = 'Order updated successfully'
    response_object['data'] = {
        'order': order.to_json()
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/delete/<int:order_id>', methods=['DELETE'])
@authenticate
def delete_order(user_id, order_id):
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    order = Order.query.get(order_id)
    if not order:
        response_object['message'] = 'Order does not exist'
        return jsonify(response_object), 404

    user = User.query.get(user_id)
    if order.user_id != user_id and not user.is_admin:
        response_object['message'] = "You don't have permission to delete this order"
        return jsonify(response_object), 401

    # delete order items
    order_items = Order_Sku.query.filter_by(order_id=order.id).all()
    for order_item in order_items:
        # delete coupon
        coupon = Coupon.query.get(order_item.coupon_id)
        coupon.delete()

        # update sku_stock
        sku_stock = Sku_Stock.query.get(order_item.sku_stock_id)
        sku_stock.quantity += order_item.quantity
        sku_stock.update()

        # update sku
        sku = Sku.query.get(sku_stock.sku_id)
        sku.quantity += order_item.quantity

        sku.number_sold -= order_item.quantity
        sku.update()

        # delete order item
        order_item.delete()

    # delete order
    order.delete()

    response_object['status'] = 'success'
    response_object['message'] = 'Order deleted successfully'

    return jsonify(response_object), 200


@order_blueprint.route('/order/status/<int:order_id>', methods=['GET', 'PUT'])
def order_status(order_id):
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    order = Order.query.get(order_id)
    if not order:
        response_object['message'] = 'Order does not exist'
        return jsonify(response_object), 404

    """Get order status"""
    if request.method == 'GET':
        response_object['status'] = 'success'
        response_object['message'] = 'Order status retrieved successfully'
        response_object['data'] = {
            'order': order.to_json()
        }

        return jsonify(response_object), 200

    """Update order status"""
    post_data = request.get_json()
    field_types = {'status': str}

    required_fields = list(field_types.keys())

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    status = post_data.get('status')

    if str(status).lower() not in ORDER_STATUS_LIST:
        return jsonify(response_object), 400

    order.status = str(status).lower()
    order.update()

    response_object['status'] = 'success'
    response_object['message'] = 'Order status updated successfully'
    response_object['data'] = {
        'order': order.to_json()
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/get/<int:order_id>', methods=['GET'])
@authenticate
def get_order(user_id, order_id):
    response_object = {
        'status': 'fail',
        'message': 'Order does not exist'
    }

    order = Order.query.get(order_id)
    if not order:
        return jsonify(response_object), 404

    user = User.query.get(user_id)
    if order.user_id != user_id and not user.is_admin:
        response_object['message'] = 'Order does not belong to user'
        return jsonify(response_object), 401

    order_skus = Order_Sku.query.filter_by(order_id=order_id).all()

    response_object['status'] = 'success'
    response_object['message'] = 'Order retrieved successfully'
    response_object['data'] = {
        'order': order.to_json(),
        'order_skus': [order_sku.to_json() for order_sku in order_skus]
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/list', methods=['GET'])
def list_orders():
    response_object = {
        'status': 'fail',
        'message': 'Order does not exist'
    }

    orders = Order.query.all()
    if not orders:
        return jsonify(response_object), 404

    response_object['status'] = 'success'
    response_object['message'] = 'Order retrieved successfully'
    response_object['data'] = {
        'orders': [order.to_json() for order in orders]
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/get_coupon', methods=['GET'])
@authenticate
def get_coupon(user_id):
    """Get coupon"""
    coupons = Coupon.query.filter_by(user_id=user_id).all()

    response_object = {
        'status': 'success',
        'message': 'Coupon retrieved',
        'data': {
            'coupon': [coupon.to_json() for coupon in coupons if coupon.is_active]
        }
    }

    return jsonify(response_object), 200
