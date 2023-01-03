from datetime import datetime
from flask import Blueprint, jsonify, request

from project.api.authentications import authenticate
from project.exceptions import APIError
from project.api.validators import field_type_validator, required_validator

from project.models.sku_model import Campaign, Coupon, Prize
from project.models.draw_model import Draw
from project.models.user_model import User

prize_blueprint = Blueprint('prize', __name__, template_folder='templates')


@prize_blueprint.route('/prize/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@prize_blueprint.route('/prize/list', methods=['GET'])
def get_all_prize():
    """Get all prize"""
    response_object = {
        'status': True,
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
        'status': False,
        'message': 'Prize does not exist',
    }

    prize = Prize.query.filter_by(id=int(prize_id)).first()

    if not prize:
        return jsonify(response_object), 200

    response_object = {
        'status': True,
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
    prizes = Prize.query.filter_by(user_id=int(user_id)).all()
    response_object = {
        'status': True,
        'message': '{} prizes found'.format(len(prizes)),
        'data': {
            'prize': [prize.to_json() for prize in prizes]
        }
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/register', methods=['POST'])
@authenticate
def create_prize(user_id):
    """Create new prize"""
    post_data = request.get_json()
    field_types = {'name': str, 'description': str, 'image_url': str}

    required_fields = list(field_types.keys())

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    prize = Prize.query.filter(Prize.name == post_data.get('name'),
                               Prize.user_id == int(user_id)).first()
    if not prize:
        try:
            prize = Prize(
                name=post_data.get('name'),
                description=post_data.get('description'),
                image=post_data.get('image_url'),
                user_id=user_id
            )
            prize.insert()

            response_object = {
                'status': True,
                'message': 'Prize is created successfully',
                'data': {
                    'prize': prize.to_json()
                }
            }
            return jsonify(response_object), 200
        except Exception as e:
            response_object = {
                'status': False,
                'error': str(e),
                'message': 'Some error occurred. Please try again.'
            }
            return jsonify(response_object), 200

    else:
        response_object = {
            'status': False,
            'message': 'Prize already exists.',
        }
        return jsonify(response_object), 200


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
            'status': False,
            'message': 'Prize does not exist',
        }
        return jsonify(response_object), 200

    prize.name = post_data.get('name') or prize.name
    prize.description = post_data.get('description') or prize.description
    prize.image = post_data.get('image_url') or prize.image

    prize.update()

    response_object = {
        'status': True,
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
            'status': False,
            'message': 'Prize does not exist',
        }
        return jsonify(response_object), 200

    prize.delete()

    response_object = {
        'status': True,
        'message': 'Prize is deleted successfully',
    }
    return jsonify(response_object), 200


@prize_blueprint.route('/prize/upcoming-draws', methods=['GET'])
def get_pre_draws():
    """Get all pre-draws"""
    draws = Draw.query.filter(
        Draw.end_date >= datetime.now(),
        Draw.winner_id == None
    ).all()

    response_object = {
        'status': True,
        'message': '{} upcoming draw(s) found'.format(len(draws)),
        'data': {
            'draws': [draw.to_json() for draw in draws]
        }
    }

    return jsonify(response_object), 200


@prize_blueprint.route('/prize/past-draws', methods=['GET'])
def get_past_draws():
    """Get all past-draws"""
    draws = Draw.query.filter(Draw.winner_id != None).all()

    response_object = {
        'status': True,
        'message': '{} past draw(s) found'.format(len(draws)),
        'data': {
            'draws': [draw.to_json() for draw in draws]
        }
    }

    return jsonify(response_object), 200


@prize_blueprint.route('/prize/winners', methods=['GET'])
def get_winners():
    """Get all winners"""
    draws = Draw.query.filter(Draw.winner_id != None).all()
    draws = [draw.to_json() for draw in draws]

    for draw in draws:
        draw['coupon'] = Coupon.query.filter_by(
            user_id=draw['winner_id']).first().to_json()

    response_object = {
        'status': True,
        'message': '{} winner(s) found'.format(len(draws)),
        'data': {
            'draws': draws
        }
    }

    return jsonify(response_object), 200


@prize_blueprint.route('/prize/redeem-coupon', methods=['POST'])
@authenticate
def redeem_coupon(user_id):
    """Redeem coupon"""
    post_data = request.get_json()
    field_types = {'coupon_code': str}

    required_fields = list(field_types.keys())

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    coupon = Coupon.query.filter(
        Coupon.code == post_data.get('coupon_code'),
        Coupon.user_id == int(user_id)
    ).first()

    if not coupon:
        response_object = {
            'status': False,
            'message': 'Coupon does not exist',
        }
        return jsonify(response_object), 200

    if coupon.is_redeemed:
        response_object = {
            'status': False,
            'message': 'Coupon is already redeemed',
        }
        return jsonify(response_object), 200

    draw = Draw.query.filter_by(winner_id=user_id).first()

    if draw:
        campaign = Campaign.query.get(draw.campaign_id)
        prize = Prize.query.get(campaign.prize_id).to_json()
        response_object = {
            'status': True,
            'message': "Congratulations! You've won {} in lucky draw".format(prize['name']),
            'data': {
                'prize': prize
            }
        }

    else:
        response_object = {
            'status': False,
            'message': "Sorry, Try your luck next time!"
        }

    coupon.is_redeemed = True
    coupon.update()

    return jsonify(response_object), 200
