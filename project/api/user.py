import os
import base64
import logging

from flask import Blueprint, jsonify, request
from flask import current_app

from project.models import (
    User,
    Location,
    Campaign,
    Sku,
    Banners,
    ShoppingCart,
    CartItem
)

from project.api.utils import secure_file, upload_file
from project.api.authentications import authenticate

from project import db, bcrypt
from project.exceptions import APIError
from project.api.validators import email_validator, field_type_validator, required_validator


user_blueprint = Blueprint('user', __name__, template_folder='templates')
logger = logging.getLogger(__name__)


@user_blueprint.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@user_blueprint.route('/users/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@user_blueprint.route('/users/list', methods=['GET'])
def get_all_users():
    """Get all users"""
    users = User.query.all()
    response_object = {
        'status': True,
        'message': '{} users found'.format(len(users)),
        'data': {
            'users': [user.to_json() for user in users]
        }
    }
    return jsonify(response_object), 200


@user_blueprint.route('/users/get/<int:user_id>', methods=['GET'])
def get_single_user(user_id):
    """Get single user details"""
    response_object = {
        'status': False,
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(user_id)).first()

    if not user:
        return jsonify(response_object), 200

    location = Location.query.filter_by(user_id=int(user_id)).first()

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'

    response_object['data'] = user.to_json()
    response_object['data']['location'] = location.to_json(
    ) if location else None

    return jsonify(response_object), 200


@user_blueprint.route('/users/get', methods=['GET'])
@authenticate
def get_user_by_auth_token(user_id):
    """Get single user details"""
    response_object = {
        'status': False,
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(user_id)).first()

    if not user:
        return jsonify(response_object), 200

    location = Location.query.filter_by(user_id=int(user_id)).first()

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'

    response_object['data'] = user.to_json()
    response_object['data']['location'] = location.to_json(
    ) if location else None

    return jsonify(response_object), 200


@user_blueprint.route('/users/upload', methods=['POST'])
@authenticate
def upload_picture(user_id):
    filename = None
    try:
        file = request.files['file']
        if file:
            # create secure filename and save locally
            secured_file = secure_file(file)
            filename = secured_file["filename"]

            # get current path
            current_path = os.path.dirname(os.path.abspath(__name__))
            file_path = os.path.join(current_path, filename)
            logger.info("File path: {}".format(file_path))

            with open(file_path, mode="rb") as img:
                imgstr = base64.b64encode(img.read())

            response = upload_file(imgstr, filename)

            object_url = response.url
            logger.info("File uploaded successfully: {}".format(object_url))

            # delete file locally
            os.remove(filename)

            user = User.query.filter_by(id=int(user_id)).first()

            if not user:
                return jsonify({
                    'message': 'User does not exist',
                    'status': False
                }), 200

            user.profile_picture = object_url
            user.update()

            message = "File uploaded successfully!"

            return jsonify({
                "message": message,
                "status": True,
                "data": user.to_json()
            }), 200

        else:
            return jsonify({
                "message": "Invalid payload: file not found!",
                "status": False
            }), 200

    except Exception as e:
        try:
            logger.error("Error uploading file: {}".format(e))
            os.remove(filename)
        except:
            pass
        finally:
            return jsonify({"message": str(e), "status": False}), 200


@user_blueprint.route('/users/update_info', methods=['PATCH'])
@authenticate
def update_user_info(user_id):
    """Update user info"""
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    if not post_data:
        return jsonify(response_object), 200

    try:
        user = User.query.get(user_id)

        field_types = {
            "firstname": str, "lastname": str, "email": str,
            "password": str, "dob": str, "gender": str,
            "mobile_no": str, "profile_picture": str, "active": bool,
            "location": dict
        }

        post_data = field_type_validator(post_data, field_types)
        if post_data.get("email"):
            email_validator(post_data.get("email"))

        password = post_data.get('password')

        if password:
            user.password = bcrypt.generate_password_hash(
                password, current_app.config.get("BCRYPT_LOG_ROUNDS")).decode()

        user.firstname = post_data.get('firstname') or user.firstname
        user.lastname = post_data.get('lastname') or user.lastname
        user.email = post_data.get('email') or user.email
        user.mobile_no = post_data.get("mobile_no") or user.mobile_no
        user.gender = post_data.get("gender") or user.gender
        user.dob = post_data.get("dob") or user.dob
        user.profile_picture = post_data.get(
            'profile_picture') or user.profile_picture
        user.active = post_data.get('active') or user.active

        user.update()

        loc = Location.query.filter_by(user_id=user_id).first()

        if post_data.get("location"):
            field_types = {
                "address": str, "city": str, "state": str,
                "country": str, "zipcode": str
            }

            location = post_data.get("location")
            location = field_type_validator(location, field_types)

            if not loc:
                loc = Location(
                    address=location.get("address"),
                    city=location.get("city"),
                    state=location.get("state"),
                    country=location.get("country"),
                    zipcode=location.get("zipcode"),
                    user_id=user_id
                )

                loc.insert()

            else:
                loc.address = location.get("address") or loc.address
                loc.city = location.get("city") or loc.city
                loc.state = location.get("state") or loc.state
                loc.country = location.get("country") or loc.country
                loc.zipcode = location.get("zipcode") or loc.zipcode

                loc.update()

        updated_user = user.to_json()

        updated_user['location'] = loc.to_json() if loc else None

        response_object['status'] = True
        response_object['message'] = 'User info updated successfully.'
        response_object['data'] = {
            'user': updated_user
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Error updating user info: {}".format(e))
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/update_location', methods=['PUT', 'PATCH'])
@authenticate
def update_user_location(user_id):
    """Update user location"""

    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    if not post_data:
        return jsonify(response_object), 400

    try:
        location = Location.query.filter_by(user_id=int(user_id)).first()

        field_types = {
            "address": str, "city": str, "state": str,
            "country": str, "zipcode": str
        }

        post_data = field_type_validator(post_data, field_types)

        if not location:
            required_fields = list(field_types.keys())
            required_validator(post_data, required_fields)

            location = Location(
                user_id=user_id,
                address=post_data.get('address'),
                city=post_data.get('city'),
                state=post_data.get('state'),
                country=post_data.get('country'),
                zipcode=post_data.get('zipcode')
            )
            location.insert()

            response_object['status'] = True
            response_object['message'] = 'User location added successfully.'
            response_object['location'] = location.to_json()

            return jsonify(response_object), 200

        location.address = post_data.get('address') or location.address
        location.city = post_data.get('city') or location.city
        location.state = post_data.get('state') or location.state
        location.country = post_data.get('country') or location.country
        location.zipcode = post_data.get('zipcode') or location.zipcode

        location.update()

        response_object['status'] = True
        response_object['message'] = 'User location updated successfully.'
        response_object['data'] = {
            'location': location.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/home/mobile', methods=['GET'])
@authenticate
def get_user_mobile_home(user_id):
    """
    Get user home page which includes: 
        - User (name, profile_picture)
        - Campaign (carousal, list, closing)
        - Banners
    """
    response_object = {
        'status': False,
        'data': {},
    }

    try:
        user = User.query.get(user_id)
        response_object['data']['user'] = user.to_json()

        # get closing and carousal campaigns
        campaigns = Campaign.query.filter_by(is_active=True).all()

        active, closing, carousal = [], [], []
        for campaign in campaigns:
            sku = Sku.query.get(campaign.sku_id)
            if not sku:
                continue

            active.append(campaign.to_json())

            if (((sku.quantity - sku.number_sold) > 0) and
                    ((int((sku.number_sold / sku.quantity) * 100)) > campaign.threshold)):
                closing.append(campaign.to_json())

            else:
                carousal.append(campaign.to_json())

        # get total carts
        cart = ShoppingCart.query.filter_by(
            user_id=user_id, is_active=True).first()

        cart_length = len(CartItem.query.filter_by(
            cart_id=cart.id).all()) if cart else 0

        response_object['data']['carousal'] = carousal
        response_object['data']['closing'] = closing
        response_object['data']['active'] = active
        response_object['data']['cart_length'] = cart_length

        # get banners
        banners = Banners.query.filter_by(is_active=True).all()
        response_object['data']['banners'] = [banner.to_json()
                                              for banner in banners]

        response_object['status'] = True
        response_object['message'] = 'User home page data fetched successfully.'
        return jsonify(response_object), 200

    except Exception as e:
        response_object['message'] = str(e)
        return jsonify(response_object), 200
