import random
import string
import logging
from flask import jsonify, request, Blueprint

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from project import db, bcrypt
from project.api.credentials import *
from project.api.authentications import authenticate, require_secure_transport
from project.api.validators import email_validator, field_type_validator, required_validator
from project.models import User, BlacklistToken, Location
from project.exceptions import APIError

auth_blueprint = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)


@auth_blueprint.route('/users/auth/access_token', methods=['GET'])
@authenticate
def get_access_token(user_id):
    """Get access token"""
    user = User.query.filter_by(id=int(user_id)).first()
    if not user:
        response_object = {
            'status': False,
            'message': 'User does not exist',
        }
        return jsonify(response_object), 200

    auth_token = user.encode_auth_token(user.id)
    if auth_token:
        response_object = {
            "status": True,
            "message": "Access token generated successfully.",
            "auth_token": auth_token.decode('utf-8'),
            "id": user.id
        }

        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/login', methods=['POST'])
def login():
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    field_types = {"username": str, "password": str}
    required_fields = ["username", "password"]

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    username = post_data.get('username')
    password = post_data.get('password')

    try:
        try:
            email_validator(username)
            user = User.query.filter_by(email=username).first()
        except APIError:
            user = User.query.filter_by(mobile_no=username).first()

        if not user:
            response_object['message'] = 'Username or password is incorrect.'
            return jsonify(response_object), 200

        if bcrypt.check_password_hash(user.password, password.encode('utf-8')):
            if user.account_suspension:
                response_object['message'] = 'Account is suspended by admin.'
                return jsonify(response_object), 200

            user.active = True
            user.update()

            auth_token = user.encode_auth_token(user.id)
            if auth_token:
                response_object = {
                    "status": True,
                    "message": "User logged in successfully.",
                    "auth_token": auth_token.decode('utf-8'),
                    "id": user.id
                }

                return jsonify(response_object), 200
        else:
            response_object['message'] = 'Username or password is incorrect.'
            return jsonify(response_object), True

    except Exception as e:
        logging.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/logout', methods=['GET'])
@authenticate
def logout(user_id):
    """Logout user"""
    # get auth token
    auth_header = request.headers.get('Authorization')
    auth_token = auth_header.split(" ")[1]

    try:
        # blacklist token
        blacklist_token = BlacklistToken(token=auth_token)
        blacklist_token.insert()

        user = User.query.filter_by(id=int(user_id)).first()
        user.active = False
        user.update()

        response_object = {
            'status': True,
            'message': 'User logged out successfully.'
        }
        return jsonify(response_object), 200

    except Exception as e:
        response_object = {
            'status': False,
            'message': str(e)
        }
        return jsonify(response_object), 400


@auth_blueprint.route('/users/auth/register', methods=['POST'])
def register():
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    field_types = {
        "firstname": str, "lastname": str, "email": str,
        "mobile_no": str, "password": str, "dob": str,
        "gender": str, "profile_pic": str, "location": dict
    }

    required_fields = list(field_types.keys())
    required_fields.remove('dob')
    required_fields.remove('gender')
    required_fields.remove('profile_pic')
    required_fields.remove('location')

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)
    email_validator(post_data["email"])

    email = post_data.get('email')
    mobile_no = post_data.get("mobile_no")
    profile_pic = post_data.get('profile_pic')
    password = post_data.get('password')
    dob = post_data.get('dob')
    gender = post_data.get('gender')
    location = post_data.get('location')
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(mobile_no=mobile_no).first()

            if user:
                response_object['message'] = 'Mobile number already exists.'
                return jsonify(response_object), 200

            new_user = User(
                firstname=post_data.get('firstname'),
                lastname=post_data.get('lastname'),
                email=email,
                mobile_no=mobile_no,
                password=password
            )

            new_user.profile_pic = profile_pic or None
            new_user.dob = dob or None
            new_user.gender = gender or None
            new_user.insert()

            if location:
                Location(
                    address=location.get('address'),
                    city=location.get('city'),
                    state=location.get('state'),
                    country=location.get('country'),
                    zipcode=location.get('zipcode'),
                    user_id=new_user.id
                ).insert()

            auth_token = new_user.encode_auth_token(new_user.id)
            response_object = {
                'status': True,
                'message': 'User registered successfully.',
                'auth_token': auth_token.decode('utf-8'),
                'id': new_user.id
            }

            return jsonify(response_object), 200

        else:
            response_object['message'] = 'Email already exists.'
            return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logging.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 400


# GOOGLE login
@auth_blueprint.route('/users/auth/google_token', methods=['GET', 'POST'])
@require_secure_transport
def google_login_token():
    """
    Input: json object passed in the body of the request
    {
        'access_token': TOKEN
    }

    """
    post_data = request.get_json()
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }
    if not post_data:
        return jsonify(response_object), 200

    access_token = post_data.get('access_token')

    if not access_token:
        return jsonify(response_object), 200

    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        # try:
        #     idinfo = id_token.verify_oauth2_token(
        #         access_token, google_requests.Request(), AUTH_KEYS['GOOGLE']['CLIENT_ID_LEAPTURE'])
        # except Exception as exp:
        #     logger.error(str(exp))
        #     response_object['message'] = str(exp)
        #     idinfo = id_token.verify_oauth2_token(
        #         access_token, google_requests.Request(), AUTH_KEYS['GOOGLE']['IOS_CLIENT_ID'])

        # idinfo = id_token.verify_firebase_token(
        #     access_token, google_requests.Request(),
        #     "1:705540919954:android:bec4aefcaa7bef0ea68c4b")

        HTTP_REQUEST = google_requests.Request()
        app_id = "1:705540919954:android:bec4aefcaa7bef0ea68c4b"
        idinfo = id_token.verify_firebase_token(
            access_token, HTTP_REQUEST, app_id)

        # idinfo = id_token.verify_oauth2_token(
        #     access_token, google_requests.Request())

        logger.info(idinfo)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_object = {"email": idinfo.get("email"), "first_name": idinfo.get("family_name"),
                       "last_name": idinfo.get("given_name"), "profile_pic": idinfo.get("picture")}

        if social_media_check_user_exists(user_object["email"]):
            login = login_social_media(user_object)
            if login:
                return jsonify(login), 200
            else:
                return jsonify(response_object)

        else:
            user_object['password'] = random_string(10)

            new_user = User(
                firstname=user_object['first_name'],
                lastname=user_object['last_name'],
                email=user_object['email'],
                mobile_no=None,
                password=user_object['password']
            )

            new_user.active = False
            new_user.profile_picture = user_object.get('profile_pic') or None

            new_user.insert()

            auth_token = new_user.encode_auth_token(new_user.id)
            response_object = {
                'status': True,
                'message': 'User registered successfully.',
                'auth_token': auth_token.decode('utf-8'),
                'id': new_user.id
            }
            return jsonify(response_object), 200

    except ValueError as ex:
        logging.error(ex)
        response_object['message'] = str(ex)
        return jsonify(response_object), 400


def random_string(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def social_media_check_user_exists(email):
    # check for existing user
    user = User.query.filter_by(email=email).first()

    return True if user else False


def login_social_media(user_profile):
    try:
        # fetch the user data
        user = User.query.filter_by(email=user_profile.get('email')).first()
        if user:
            auth_token = user.encode_auth_token(user.id)
            if auth_token:
                response_object = {
                    'status': True,
                    'message': 'User logged in successfully.',
                    'auth_token': auth_token.decode('utf-8'),
                    'id': user.id
                }
                return jsonify(response_object), 200

        else:
            return None

    except Exception as e:
        return None


@auth_blueprint.route('/users/auth/verify', methods=['POST'])
def auth_login():
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    field_types = {"username": str}
    required_fields = ["username"]

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)

    username = post_data.get('username')

    try:
        try:
            email_validator(username)
            user = User.query.filter_by(email=username).first()
        except APIError:
            user = User.query.filter_by(mobile_no=username).first()

        if not user:
            response_object['message'] = 'User does not exist'
            return jsonify(response_object), 200

        if user.account_suspension:
            response_object['message'] = 'Account is suspended by admin.'
            return jsonify(response_object), 200

        user.active = True
        user.update()

        auth_token = user.encode_auth_token(user.id)
        if auth_token:
            response_object = {
                "status": True,
                "message": "User logged in successfully.",
                "auth_token": auth_token.decode('utf-8'),
                "id": user.id
            }

            return jsonify(response_object), 200

    except Exception as e:
        logging.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 200
