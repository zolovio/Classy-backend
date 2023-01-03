from datetime import datetime
from flask import Blueprint, jsonify, request

from project.api.authentications import authenticate
from project.exceptions import APIError
from project.api.validators import field_type_validator, required_validator

from project.models import Campaign, Sku, Prize, Draw

campaign_blueprint = Blueprint(
    'campaign', __name__, template_folder='templates')


@campaign_blueprint.route('/campaign/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@campaign_blueprint.route('/campaign/list', methods=['GET'])
def get_all_campaign():
    """Get all active campaigns"""
    campaigns = Campaign.query.all()

    response_object = {
        'status': True,
        'message': '{} active campaign(s) found'.format(len(campaigns)),
        'data': {
            'campaign': [campaign.to_json() for campaign in campaigns if campaign.is_active]
        }
    }
    return jsonify(response_object), 200


@campaign_blueprint.route('/campaign/carousel', methods=['GET'])
def get_carousel_campaign():
    """Get all active campaigns"""
    campaigns = Campaign.query.all()

    response_object = {
        'status': True,
        'message': '{} active campaign(s) found'.format(len(campaigns)),
        'data': {
            'campaign': [campaign.to_json() for campaign in campaigns if campaign.is_active]
        }
    }
    return jsonify(response_object), 200


@campaign_blueprint.route('/campaign/get/<int:campaign_id>', methods=['GET'])
def get_single_campaign(campaign_id):
    """Get single campaign details"""
    response_object = {
        'status': False,
        'message': 'Campaign does not exist',
    }

    campaign = Campaign.query.filter_by(id=int(campaign_id)).first()

    if not campaign:
        return jsonify(response_object), 200

    response_object['status'] = True
    response_object['message'] = 'Campaign exists and is returned'
    response_object['data'] = {
        'campaign': campaign.to_json()
    }

    return jsonify(response_object), 200


@campaign_blueprint.route('/campaign/get', methods=['GET'])
@authenticate
def get_campaign(user_id):
    """Get all campaign"""
    campaigns = Campaign.query.filter_by(user_id=int(user_id)).all()
    response_object = {
        'status': True,
        'message': '{} campaign(s) found'.format(len(campaigns)),
        'data': {
            'campaign': [campaign.to_json() for campaign in campaigns]
        }
    }
    return jsonify(response_object), 200


@campaign_blueprint.route('/campaign/status/<int:campaign_id>', methods=['GET'])
@authenticate
def get_campaign_status(user_id, campaign_id):
    """Get single campaign details"""
    response_object = {
        'status': False,
        'message': 'Campaign does not exist',
    }

    try:
        required_validator(request.args, ['is_active'], "Parameter")

        is_active = bool(int(request.args.get('is_active')))
        campaign = Campaign.query.filter(Campaign.id == int(
            campaign_id), Campaign.user_id == int(user_id)).first()

        if not campaign:
            return jsonify(response_object), 200

        campaign.start_date = datetime.now() if is_active else None
        campaign.is_active = is_active

        campaign.update()

        response_object['status'] = True
        response_object['message'] = 'Campaign {} status updated to {}'.format(
            campaign.name, is_active)

        return jsonify(response_object), 200

    except Exception as e:
        response_object = {
            'status': 'fail',
            'message': str(e),
        }

        return jsonify(response_object), 400


@campaign_blueprint.route('/campaign/closing', methods=['GET'])
def get_closing_campaigns():
    response_object = {
        'status': True,
        'message': 'No closing campaign found',
        'data': {}
    }

    campaigns = Campaign.query.all()
    closing_campaigns = []

    for campaign in campaigns:
        if not campaign.is_active:
            continue

        sku = Sku.query.get(campaign.sku_id)

        if (((sku.quantity - sku.number_sold) > 0) and
                ((int((sku.number_sold / sku.quantity) * 100)) > campaign.threshold)):

            closing_campaigns.append(campaign.to_json())

    response_object['message'] = '{} closing campaign(s) found'.format(
        len(closing_campaigns))
    response_object['data'] = {'campaign': closing_campaigns}

    return jsonify(response_object), 200


@campaign_blueprint.route('/campaign/register', methods=['POST'])
@authenticate
def create_campaign(user_id):
    """Create new campaign"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }
    try:
        post_data = request.get_json()
        field_types = {'name': str, 'description': str, 'prize_id': int,
                       'threshold': int, 'video_url': str, 'sku_id': int,
                       'image_url': str, 'start_date': str, 'end_date': str}

        required_fields = list(field_types.keys())
        required_fields.remove('start_date')
        required_fields.remove('end_date')
        required_fields.remove('threshold')

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        # check if prize exists
        prize = Prize.query.get(post_data.get('prize_id'))
        if not prize:
            response_object['message'] = 'Prize does not exist'
            return jsonify(response_object), 200

        # check if sku exists
        sku = Sku.query.get(post_data.get('sku_id'))
        if not sku:
            response_object['message'] = 'SKU does not exist'
            return jsonify(response_object), 200

        campaign = Campaign.query.filter(Campaign.name == post_data.get('name'),
                                         Campaign.user_id == int(user_id)).first()
        if not campaign:
            campaign = Campaign(
                name=post_data.get('name'),
                description=post_data.get('description'),
                prize_id=post_data.get('prize_id'),
                threshold=post_data.get('threshold') or 80,  # default 80%
                sku_id=post_data.get('sku_id'),
                image=post_data.get('image_url'),
                start_date=post_data.get('start_date'),
                end_date=post_data.get('end_date'),
                user_id=user_id
            )
            campaign.insert()

            Draw(
                campaign_id=campaign.id,
                video_url=post_data.get('video_url'),
            ).insert()

            response_object['status'] = True
            response_object['message'] = 'Campaign is created successfully'
            response_object['data'] = {
                'campaign': campaign.to_json()
            }

            return jsonify(response_object), 200

        else:
            response_object['message'] = 'Campaign already exists'
            return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400


@campaign_blueprint.route('/campaign/update/<int:campaign_id>', methods=['PUT', 'PATCH'])
@authenticate
def update_campaign(user_id, campaign_id):
    """Update campaign"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    try:
        post_data = request.get_json()
        field_types = {'name': str, 'description': str, 'prize_id': int,
                       'is_active': bool, 'threshold': int, 'sku_id': int,
                       'image_url': str, 'start_date': str, 'end_date': str}

        post_data = field_type_validator(post_data, field_types)

        campaign = Campaign.query.filter(Campaign.id == int(campaign_id),
                                         Campaign.user_id == int(user_id)).first()

        if not campaign:
            response_object['message'] = 'Campaign does not exist'
            return jsonify(response_object), 200

        campaign.name = post_data.get('name') or campaign.name
        campaign.description = post_data.get(
            'description') or campaign.description
        campaign.prize_id = post_data.get('prize_id') or campaign.prize_id
        campaign.sku_id = post_data.get('sku_id') or campaign.sku_id
        campaign.image = post_data.get('image_url') or campaign.image
        campaign.threshold = post_data.get('threshold') or campaign.threshold
        campaign.start_date = post_data.get(
            'start_date') or campaign.start_date
        campaign.end_date = post_data.get('end_date') or campaign.end_date

        campaign.is_active = post_data.get('is_active') if post_data.get('is_active') is not None \
            else campaign.is_active

        campaign.update()

        response_object['status'] = True
        response_object['message'] = 'Campaign is updated successfully'
        response_object['data'] = {
            'campaign': campaign.to_json()
        }
        return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400


@campaign_blueprint.route('/campaign/delete/<int:campaign_id>', methods=['DELETE'])
@authenticate
def delete_campaign(user_id, campaign_id):
    """Delete campaign"""
    response_object = {
        'status': False,
        'message': 'Invalid payload',
    }

    try:
        campaign = Campaign.query.filter(Campaign.id == int(campaign_id),
                                         Campaign.user_id == int(user_id)).first()

        if not campaign:
            response_object['message'] = 'Campaign does not exist'
            return jsonify(response_object), 200

        campaign.delete()

        response_object['status'] = True
        response_object['message'] = 'Campaign is deleted successfully'

        return jsonify(response_object), 200

    except Exception as e:
        response_object['error'] = str(e)
        response_object['message'] = 'Some error occurred. Please try again.'
        return jsonify(response_object), 400
