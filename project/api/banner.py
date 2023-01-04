from flask import Blueprint, jsonify, request

from project.models import Banners
from project.api.authentications import authenticate
from project.api.validators import field_type_validator, required_validator

banner_blueprint = Blueprint('banner', __name__, template_folder='./templates')


@banner_blueprint.route('/banner/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@banner_blueprint.route('/banner/get', methods=['GET'])
@authenticate
def get_user_banners(user_id):
    """Get user banners"""

    banners = Banners.query.filter(Banners.user_id == int(user_id)).all()

    response_object = {
        'status': True,
        'message': '{} banner(s) found'.format(len(banners)),
        'data': {
            'banners': [banner.to_json() for banner in banners]
        }
    }

    return jsonify(response_object), 200


@banner_blueprint.route('/banner/list', methods=['GET'])
def get_all_banners():
    """Get all active banners"""

    banners = Banners.query.filter_by(is_active=True).all()

    response_object = {
        'status': True,
        'message': '{} active banner(s) found'.format(len(banners)),
        'data': {
            'banners': [banner.to_json() for banner in banners]
        }
    }

    return jsonify(response_object), 200


@banner_blueprint.route('/banner/register', methods=['POST'])
@authenticate
def register_banner(user_id):
    """Register user banner"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    try:
        post_data = request.get_json()
        field_types = {'image_url': str, 'is_active': bool}
        required_fields = ['image_url']

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        image_url = post_data.get('image_url')

        banner = Banners.query.filter(
            Banners.user_id == int(user_id),
            Banners.image == image_url
        ).first()

        is_active = post_data.get('is_active') if post_data.get(
            'is_active') is not None else True

        if not banner:
            banner = Banners(
                image=post_data.get('image_url'),
                is_active=is_active,
                user_id=user_id
            )
            banner.insert()

            response_object['status'] = True
            response_object['message'] = 'Banner is created successfully'
            response_object['data'] = {
                'banner': banner.to_json()
            }

            return jsonify(response_object), 200

        else:
            response_object['message'] = 'Banner already exists'
            return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400


@banner_blueprint.route('/banner/status/<int:banner_id>', methods=['GET'])
@authenticate
def update_banner_status(user_id, banner_id):
    """Get or update banner status"""

    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    try:
        required_validator(request.args, ['is_active'], "Parameter")

        is_active = bool(int(request.args.get('is_active')))

        banner = Banners.query.filter(
            Banners.id == int(banner_id),
            Banners.user_id == int(user_id)
        ).first()

        if not banner:
            response_object['message'] = 'Banner does not exist'
            return jsonify(response_object), 200

        banner.is_active = is_active if is_active is not None else banner.is_active

        banner.update()

        response_object['status'] = True
        response_object['message'] = 'Banner {} status changed to {}'.format(
            banner.id, is_active)

        return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400


@banner_blueprint.route('/banner/delete/<int:banner_id>', methods=['DELETE'])
@authenticate
def delete_banner(user_id, banner_id):
    """Delete banner"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    try:
        banner = Banners.query.filter(
            Banners.id == int(banner_id),
            Banners.user_id == int(user_id)
        ).first()

        if not banner:
            response_object['message'] = 'Banner does not exist'
            return jsonify(response_object), 200

        banner.delete()

        response_object['status'] = True
        response_object['message'] = 'Banner is deleted successfully'

        return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400
