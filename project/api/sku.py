import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from project.api.authentications import authenticate
from project.exceptions import APIError
from project.api.validators import field_type_validator, required_validator

from project.models.sku_model import Sku, Sku_Images, Sku_Stock

sku_blueprint = Blueprint('sku', __name__, template_folder='templates')


@sku_blueprint.route('/sku/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong V0.1!'
    })


@sku_blueprint.route('/sku/list', methods=['GET'])
def get_all_sku():
    """Get all sku"""
    response_object = {
        'status': 'success',
        'message': 'All sku are returned successfully',
        'data': {
            'sku': [sku.to_json() for sku in Sku.query.all()]
        }
    }
    return jsonify(response_object), 200


@sku_blueprint.route('/sku/get/<int:sku_id>', methods=['GET'])
def get_single_sku(sku_id):
    """Get single sku details"""
    response_object = {
        'status': 'fail',
        'message': 'Sku does not exist',
    }

    sku = Sku.query.filter_by(id=int(sku_id)).first()

    if not sku:
        return jsonify(response_object), 404

    response_object = {
        'status': 'success',
        'message': 'Sku exists and is returned',
        'data': {
            'sku': sku.to_json()
        }
    }
    return jsonify(response_object), 200


@sku_blueprint.route('/sku/get', methods=['GET'])
@authenticate
def get_sku_by_user_id(user_id):
    """Get all sku by user_id"""
    skus = Sku.query.filter_by(user_id=user_id).all()

    response_object = {
        'status': 'success',
        'data': {
            'sku': [sku.to_json() for sku in skus]
        }
    }
    return jsonify(response_object), 200


@sku_blueprint.route('/sku/register', methods=['POST'])
@authenticate
def add_sku(user_id):
    """Add a new sku"""
    post_data = request.get_json()

    field_types = {
        'name': str,
        'description': str,
        'category': str,
        'price': float,
        'number_sold': int,
        'number_delivered': int,
        'size_chart': str,
        'images': list,
        'stocks': list
    }

    required_fields = list(field_types.keys())
    required_fields.remove('number_sold')
    required_fields.remove('number_delivered')

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    try:
        sku = Sku(
            name=post_data.get('name'),
            description=post_data.get('description'),
            category=post_data.get('category'),
            price=post_data.get('price'),
            quantity=0,  # will be updated later using stock
            number_sold=post_data.get('number_sold') or 0,
            number_delivered=post_data.get('number_delivered') or 0,
            size_chart=post_data.get('size_chart'),
            user_id=user_id
        )

        sku.insert()

        sku_images = post_data.get('images')
        if not sku_images:
            raise APIError('Please provide at least one image')

        for sku_image in sku_images:
            Sku_Images(sku_id=sku.id, image=sku_image).insert()

        sku_stocks = post_data.get('stocks')
        if not sku_stocks:
            raise APIError('Please provide at least one stock')

        for stock in sku_stocks:
            Sku_Stock(
                sku_id=sku.id,
                size=stock.get('size'),
                color=stock.get('color'),
                stock=stock.get('stock')
            ).insert()

            sku.quantity += stock.get('stock')

        sku.update()

        response_object = {
            'status': 'success',
            'message': 'Sku {} was added!'.format(post_data.get('name')),
            'data': {
                'sku': sku.to_json(),
            }
        }

        return jsonify(response_object), 201

    except Exception as e:
        response_object = {
            'status': 'fail',
            'message': 'Sku {} was not added!'.format(post_data.get('name')),
            'error': str(e),
        }
        return jsonify(response_object), 400


@sku_blueprint.route('/sku/update/<int:sku_id>', methods=['PATCH'])
@authenticate
def update_sku(user_id, sku_id):
    """Update sku details"""
    sku = Sku.query.filter_by(id=int(sku_id)).first()

    if not sku:
        response_object = {
            'status': 'fail',
            'message': 'Sku does not exist',
        }
        return jsonify(response_object), 404

    if sku.user_id != user_id:
        response_object = {
            'status': 'fail',
            'message': 'You are not authorized to update this sku',
        }
        return jsonify(response_object), 401

    post_data = request.get_json()

    field_types = {
        'name': str,
        'description': str,
        'category': str,
        'price': float,
        'number_sold': int,
        'number_delivered': int,
        'size_chart': str,
        'images': list,
        'stocks': list
    }

    post_data = field_type_validator(post_data, field_types)

    try:
        sku.name = post_data.get('name') or sku.name
        sku.description = post_data.get('description') or sku.description
        sku.category = post_data.get('category') or sku.category
        sku.price = post_data.get('price') or sku.price
        sku.number_sold = post_data.get('number_sold') or sku.number_sold
        sku.number_delivered = post_data.get(
            'number_delivered') or sku.number_delivered
        sku.size_chart = post_data.get('size_chart') or sku.size_chart

        sku_images = post_data.get('images')
        if sku_images:
            Sku_Images.query.filter_by(sku_id=sku.id).delete()
            for sku_image in sku_images:
                Sku_Images(sku_id=sku.id, image=sku_image).insert()

        sku_stocks = post_data.get('stocks')
        if sku_stocks:
            Sku_Stock.query.filter_by(sku_id=sku.id).delete()
            sku.quantity = 0
            for stock in sku_stocks:
                Sku_Stock(
                    sku_id=sku.id,
                    size=stock.get('size'),
                    color=stock.get('color'),
                    stock=stock.get('stock')
                ).insert()

                sku.quantity += stock.get('stock')

        sku.update()

        response_object = {
            'status': 'success',
            'message': 'Sku {} was updated!'.format(post_data.get('name')),
            'data': {
                'sku': sku.to_json(),
            }
        }

        return jsonify(response_object), 200

    except Exception as e:
        response_object = {
            'status': 'fail',
            'message': 'Sku {} was not updated!'.format(post_data.get('name')),
            'error': str(e),
        }
        return jsonify(response_object), 400


@sku_blueprint.route('/sku/delete/<int:sku_id>', methods=['DELETE'])
@authenticate
def delete_sku(user_id, sku_id):
    """Delete sku"""
    sku = Sku.query.filter_by(id=int(sku_id)).first()

    if not sku:
        response_object = {
            'status': 'fail',
            'message': 'Sku does not exist',
        }
        return jsonify(response_object), 404

    if sku.user_id != user_id:
        response_object = {
            'status': 'fail',
            'message': 'You are not authorized to delete this sku',
        }
        return jsonify(response_object), 401

    try:
        sku.delete()

        response_object = {
            'status': 'success',
            'message': 'Sku {} was deleted!'.format(sku.name),
        }

        return jsonify(response_object), 200

    except Exception as e:
        response_object = {
            'status': 'fail',
            'message': 'Sku {} was not deleted!'.format(sku.name),
            'error': str(e),
        }
        return jsonify(response_object), 400
