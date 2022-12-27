from flask import Blueprint, jsonify, request

from project.api.authentications import authenticate
from project.exceptions import APIError
from project.api.validators import field_type_validator, required_validator

from project.models.sku_model import Prize

prize_blueprint = Blueprint('prize', __name__, template_folder='templates')


@prize_blueprint.route('/prize/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong V0.1!'
    })


@prize_blueprint.route('/prize/list', methods=['GET'])
def get_all_prize():
    """Get all prize"""
    response_object = {
        'status': 'success',
        'message': 'All prizes are returned successfully',
        'data': {
            'prize': [prize.to_json() for prize in Prize.query.all()]
        }
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/get/<int:prize_id>', methods=['GET'])
def get_single_prize(prize_id):
    """Get single prize details"""
    response_object = {
        'status': 'fail',
        'message': 'Prize does not exist',
    }

    prize = Prize.query.filter_by(id=int(prize_id)).first()

    if not prize:
        return jsonify(response_object), 404

    response_object = {
        'status': 'success',
        'message': 'Prize exists and is returned',
        'data': {
            'prize': prize.to_json()
        }
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/get', methods=['GET'])
@authenticate
def get_prize(user_id):
    """Get all prize"""
    response_object = {
        'status': 'success',
        'message': 'All prizes are returned successfully',
        'data': {
            'prize': [prize.to_json() for prize in Prize.query.filter_by(user_id=int(user_id)).all()]
        }
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/create', methods=['POST'])
@authenticate
def create_prize(user_id):
    """Create new prize"""
    post_data = request.get_json()
    field_types = {'name': str, 'description': str, 'image_url': str}

    required_fields = list(field_types.keys())
    required_fields.remove('image_url')

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    prize = Prize.query.filter(Prize.name == post_data.get('name'),
                               Prize.user_id == int(user_id)).first()
    if not prize:
        try:
            prize = Prize(
                name=post_data.get('name'),
                description=post_data.get('description'),
                user_id=user_id
            )
            prize.insert()

            response_object = {
                'status': 'success',
                'message': 'Prize is created successfully',
                'data': {
                    'prize': prize.to_json()
                }
            }
            return jsonify(response_object), 201
        except Exception as e:
            response_object = {
                'status': 'fail',
                'error': str(e),
                'message': 'Some error occurred. Please try again.'
            }
            return jsonify(response_object), 401

    else:
        response_object = {
            'status': 'fail',
            'message': 'Prize already exists.',
        }
        return jsonify(response_object), 400


@prize_blueprint.route('/prize/update/<int:prize_id>', methods=['PUT', 'PATCH'])
@authenticate
def update_prize(user_id, prize_id):
    """Update prize"""
    post_data = request.get_json()
    field_types = {'name': str, 'description': str, 'image_url': str}

    post_data = field_type_validator(post_data, field_types)

    prize = Prize.query.filter(Prize.id == int(prize_id),
                               Prize.user_id == int(user_id)).first()

    if not prize:
        response_object = {
            'status': 'fail',
            'message': 'Prize does not exist',
        }
        return jsonify(response_object), 404

    prize.name = post_data.get('name') or prize.name
    prize.description = post_data.get('description') or prize.description
    prize.image_url = post_data.get('image_url') or prize.image_url

    prize.update()

    response_object = {
        'status': 'success',
        'message': 'Prize is updated successfully',
        'data': {
            'prize': prize.to_json()
        }
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/delete/<int:prize_id>', methods=['DELETE'])
@authenticate
def delete_prize(user_id, prize_id):
    """Delete prize"""
    prize = Prize.query.filter(Prize.id == int(prize_id),
                               Prize.user_id == int(user_id)).first()

    if not prize:
        response_object = {
            'status': 'fail',
            'message': 'Prize does not exist',
        }
        return jsonify(response_object), 404

    prize.delete()

    response_object = {
        'status': 'success',
        'message': 'Prize is deleted successfully',
    }
    return jsonify(response_object), 200
