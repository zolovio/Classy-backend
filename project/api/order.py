import os
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from project import db
from project.api.utils import refresh_campaigns
from project.api.authentications import authenticate
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
                     'delivered', 'cancelled', 'returned']


@order_blueprint.route('/order/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@order_blueprint.route('/order/create', methods=['POST'])
@authenticate
def create_order(user_id):
    """Create order"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        post_data = request.get_json()
        field_types = {'shipping_fee': float, 'location_id': int}

        required_fields = list(field_types.keys())
        required_fields.remove('location_id')

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        shipping_fee = post_data.get('shipping_fee')
        location_id = post_data.get('location_id')

        shopping_cart = ShoppingCart.query.filter_by(
            user_id=user_id, is_active=True).first()

        if not shopping_cart:
            response_object['message'] = 'Cart does not exist'
            return jsonify(response_object), 200

        if shopping_cart.user_id != user_id:
            response_object['message'] = 'Cart does not belong to user'
            return jsonify(response_object), 200

        if not shopping_cart.checkedout_at:
            response_object['message'] = 'Cart is not checked out yet'
            return jsonify(response_object), 200

        if location_id:
            location = Location.query.get(location_id)

        else:
            location = Location.query.filter_by(user_id=user_id).first()

        if not location:
            response_object['message'] = 'Location not found, please add one'
            return jsonify(response_object), 200

        order = Order(
            user_id=user_id,
            location_id=location.id,
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
                create_date=datetime.utcnow(),
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
            # sku.quantity -= order_sku.quantity
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

        refresh_campaigns()

        response_object['status'] = True
        response_object['message'] = 'Order created successfully'
        response_object['data'] = {
            'order_id': order.id,
            'order': order.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@order_blueprint.route('/order/update/<int:order_id>', methods=['PATCH'])
@authenticate
def update_order(user_id, order_id):
    """Update order"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        post_data = request.get_json()
        field_types = {'shipping_fee': float, 'location_id': int,
                       'order_sku_id': int, 'quantity': int}

        post_data = field_type_validator(post_data, field_types)

        shipping_fee = post_data.get('shipping_fee')
        location_id = post_data.get('location_id')
        order_sku_id = post_data.get('order_sku_id')

        order = Order.query.get(order_id)
        if not order:
            response_object['message'] = 'Order does not exist'
            return jsonify(response_object), 200

        if order.user_id != user_id:
            response_object['message'] = 'Order does not belong to user'
            return jsonify(response_object), 200

        if location_id:
            location = Location.query.get(location_id)

        else:
            location = Location.query.filter_by(user_id=user_id).first()

        if not location:
            response_object['message'] = 'Location not found, please update'
            return jsonify(response_object), 200

        if order_sku_id:
            required_validator(post_data, ['quantity'])
            quantity = post_data.get('quantity')

            order_sku = Order_Sku.query.filter_by(
                order_id=order_id, id=order_sku_id).first()
            if not order_sku:
                response_object['message'] = 'Order sku not found'
                return jsonify(response_object), 200

            sku_stock = Sku_Stock.query.get(order_sku.sku_stock_id)
            if not sku_stock:
                response_object['message'] = 'Sku stock not found'
                return jsonify(response_object), 200

            sku = Sku.query.get(sku_stock.sku_id)
            if not sku:
                response_object['message'] = 'Sku not found'
                return jsonify(response_object), 200

            if quantity < order_sku.quantity:
                sku_stock.stock += order_sku.quantity - quantity
                sku_stock.update()

                sku.number_sold -= order_sku.quantity - quantity
                sku.update()

                order.total_quantity -= order_sku.quantity - quantity
                order.total_amount -= sku.price * \
                    (order_sku.quantity - quantity)
                order.total_tax -= sku.sales_tax * \
                    (order_sku.quantity - quantity)

            elif quantity > order_sku.quantity:
                if (quantity - order_sku.quantity) > sku_stock.stock:
                    response_object['message'] = 'Not enough stock'
                    return jsonify(response_object), 200

                sku_stock.stock -= quantity - order_sku.quantity
                sku_stock.update()

                sku.number_sold += quantity - order_sku.quantity
                sku.update()

                order.total_quantity += quantity - order_sku.quantity
                order.total_amount += sku.price * \
                    (quantity - order_sku.quantity)
                order.total_tax += sku.sales_tax * \
                    (quantity - order_sku.quantity)

            if quantity == 0:
                coupon = Coupon.query.filter_by(
                    user_id=user_id,
                    sku_stock_id=order_sku.sku_stock_id
                ).first()

                order_sku.delete()
                coupon.delete()

            else:
                order_sku.quantity = quantity
                order_sku.total_price = sku.price * quantity
                order_sku.sales_tax = sku.sales_tax * quantity
                order_sku.update()

        order.shipping_fee = shipping_fee or order.shipping_fee
        order.location_id = location_id or order.location_id
        order.update()

        refresh_campaigns()

        response_object['status'] = True
        response_object['message'] = 'Order updated successfully'
        response_object['data'] = {
            'order_id': order.id,
            'order': order.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@order_blueprint.route('/order/delete/<int:order_id>', methods=['DELETE'])
@authenticate
def delete_order(user_id, order_id):
    """Delete order"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        order = Order.query.get(order_id)
        if not order:
            response_object['message'] = 'Order does not exist'
            return jsonify(response_object), 200

        user = User.query.get(user_id)
        if order.user_id != user_id and not user.is_admin:
            response_object['message'] = "You don't have permission to delete this order"
            return jsonify(response_object), 200

        # delete order items
        order_items = Order_Sku.query.filter_by(order_id=order.id).all()
        for order_item in order_items:
            # delete coupon
            coupon = Coupon.query.get(order_item.coupon_id)
            coupon.delete()

            # update sku_stock
            sku_stock = Sku_Stock.query.get(order_item.sku_stock_id)
            sku_stock.stock += order_item.quantity
            sku_stock.update()

            # update sku
            sku = Sku.query.get(sku_stock.sku_id)
            # sku.quantity += order_item.quantity

            sku.number_sold -= order_item.quantity
            sku.update()

            # delete order item
            order_item.delete()

        # delete order
        order.delete()

        response_object['status'] = True
        response_object['message'] = 'Order deleted successfully'

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@order_blueprint.route('/order/status/<int:order_id>', methods=['GET', 'PUT'])
def order_status(order_id):
    """Get or update order status"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    order = Order.query.get(order_id)
    if not order:
        response_object['message'] = 'Order does not exist'
        return jsonify(response_object), 200

    """Get order status"""
    if request.method == 'GET':
        response_object['status'] = True
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
        return jsonify(response_object), 200

    status = str(status).lower()

    response_object['message'] = 'Invalid status change from {} to {}'.format(
        order.status, status)

    # verify status change
    if status == 'delivered' and order.status != 'shipped':
        return jsonify(response_object), 200

    if status == 'shipped' and order.status != 'paid':
        return jsonify(response_object), 200

    if status == 'paid' and order.status != 'pending':
        return jsonify(response_object), 200

    if status == 'cancelled' and order.status != 'pending':
        return jsonify(response_object), 200

    if status in 'returned' and order.status != 'delivered':
        return jsonify(response_object), 200

    if status == 'cancelled':
        for order_sku in Order_Sku.query.filter_by(order_id=order_id).all():
            # update sku_stock
            sku_stock = Sku_Stock.query.get(order_sku.sku_stock_id)
            sku_stock.stock += order_sku.quantity
            sku_stock.update()

            # update sku number_sold
            sku = Sku.query.get(sku_stock.sku_id)
            sku.number_sold -= order_sku.quantity
            sku.update()

    if status == 'delivered':
        # update booking_date
        order.booking_date = datetime.now()

        for order_sku in Order_Sku.query.filter_by(order_id=order_id).all():
            sku_stock = Sku_Stock.query.get(order_sku.sku_stock_id)

            # update sku number_delivered
            sku = Sku.query.get(sku_stock.sku_id)
            sku.number_delivered += order_sku.quantity
            sku.update()

            refresh_campaigns()

    if status == 'returned':
        # return within 7 days
        if (datetime.now() - order.booking_date).days > 7:
            response_object['message'] = 'Order cannot be returned after 7 days'
            return jsonify(response_object), 200

        for order_sku in Order_Sku.query.filter_by(order_id=order_id).all():
            # update sku_stock
            sku_stock = Sku_Stock.query.get(order_sku.sku_stock_id)
            sku_stock.stock += order_sku.quantity
            sku_stock.update()

            # update sku number_sold
            sku = Sku.query.get(sku_stock.sku_id)
            sku.number_sold -= order_sku.quantity
            sku.number_delivered -= order_sku.quantity
            sku.update()

            refresh_campaigns()

    order.status = status
    order.update()

    response_object['status'] = True
    response_object['message'] = 'Order status updated successfully'
    response_object['data'] = {
        'order': order.to_json()
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/get/<int:order_id>', methods=['GET'])
@authenticate
def get_order(user_id, order_id):
    """Get order"""

    response_object = {
        'status': False,
        'message': 'Order does not exist'
    }

    order = Order.query.get(order_id)
    if not order:
        return jsonify(response_object), 200

    user = User.query.get(user_id)
    if order.user_id != user_id and not user.is_admin:
        response_object['message'] = 'Order does not belong to user'
        return jsonify(response_object), 200

    order_skus = Order_Sku.query.filter_by(order_id=order_id).all()

    response_object['status'] = True
    response_object['message'] = 'Order retrieved successfully'
    response_object['data'] = {
        'order': order.to_json(),
        'order_skus': [order_sku.to_json() for order_sku in order_skus]
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/get', methods=['GET'])
@authenticate
def get_orders(user_id):
    """Get orders"""

    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    status = request.args.get('status')

    if status and status in ORDER_STATUS_LIST:
        status = str(status).lower()
    else:
        status = None

    if status:
        logger.info('status: {}'.format(status))
        orders = Order.query.filter_by(user_id=user_id, status=status).all()

    else:
        orders = Order.query.filter_by(user_id=user_id).all()

    response_object['status'] = True
    response_object['message'] = '{} order(s) found of {} status'.format(
        len(orders), status if status else 'any')
    response_object['data'] = {
        'orders': [order.to_json() for order in orders]
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/list', methods=['GET'])
def list_orders():
    """List orders"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    status = request.args.get('status')
    status = str(status).lower()

    if status and status in ORDER_STATUS_LIST:
        logger.info('status: {}'.format(status))
        orders = Order.query.filter_by(status=status).all()

    else:
        orders = Order.query.all()

    response_object['status'] = True
    response_object['message'] = '{} order(s) found of {} status'.format(
        len(orders), status if status else 'any')
    response_object['data'] = {
        'orders': [order.to_json() for order in orders]
    }

    return jsonify(response_object), 200


@order_blueprint.route('/order/get_coupon', methods=['GET'])
@authenticate
def get_coupon(user_id):
    """Get coupon"""
    coupons = Coupon.query.filter_by(user_id=int(user_id)).all()

    response_object = {
        'status': True,
        'message': '{} coupon(s) found'.format(len(coupons)),
        'data': {
            'coupon': [coupon.to_json() for coupon in coupons]
        }
    }

    return jsonify(response_object), 200
