import logging
from flask import Flask, redirect, url_for, session, jsonify, request, Blueprint

from project import db, bcrypt
from project.models.user_model import User, BlacklistToken
from project.api.authentications import authenticate
from project.api.validators import email_validator, field_type_validator, required_validator
from project.exceptions import APIError

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/users/auth/access_token', methods=['GET'])
@authenticate
def get_access_token(resp):
    user = User.query.filter_by(id=resp).first()
    email = user.email

    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }
    user = User.query.filter(User.email==email).first()
    if user:
        auth_token = user.encode_auth_token(user.id)
        response_object['status'] = 'success'
        del response_object["message"]
        response_object['auth_token'] = auth_token.decode()
        return jsonify(response_object), 200
    else:
        return jsonify(response_object), 400


@auth_blueprint.route('/users/auth/login', methods=['POST'])
def login():
    post_data = request.get_json()

    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 400

    field_types = {"email": str, "password": str}
    required_fields = ["email", "password"]

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)
    email_validator(post_data["email"])

    email = post_data.get('email')
    password = post_data.get('password')

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            response_object['message'] = 'User does not exist.'
            return jsonify(response_object), 404

        if bcrypt.check_password_hash(user.password, password.encode('utf-8')):
            if user.account_suspension:
                response_object['message'] = 'Account is suspended by admin.'
                return jsonify(response_object), 400

            user.active = True
            user.update()

            auth_token = user.encode_auth_token(user.id)
            if auth_token:
                response_object = {
                    "status": "success",
                    "message": "Successfully logged in.",
                    "auth_token": auth_token.decode('utf-8'),
                    "id": user.id
                }

                return jsonify(response_object), 200
        else:
            response_object['message'] = 'Invalid credentials.'
            return jsonify(response_object), 401

    except Exception as e:
        logging.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 500

@auth_blueprint.route('/users/auth/logout', methods=['GET'])
@authenticate
def logout(resp):
    """Logout user"""
    # get auth token
    auth_header = request.headers.get('Authorization')
    auth_token = auth_header.split(" ")[1]

    try:
        # blacklist token
        blacklist_token = BlacklistToken(token=auth_token)
        blacklist_token.insert()

        user = User.query.filter_by(id=resp).first()
        user.active = False
        user.update()

        response_object = {
            'status': 'success',
            'message': 'Successfully logged out.'
        }
        return jsonify(response_object), 200

    except Exception as e:
        response_object = {
            'status': 'fail',
            'message': str(e)
        }
        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/register', methods=['POST'])
def register():
    post_data = request.get_json()

    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 400

    field_types = {
        "firstname":str, "lastname":str, "email": str, 
        "password": str, "gender": str, "profile_pic": str
    }

    required_fields = ["firstname", "lastname", "email", "password"]

    post_data = field_type_validator(post_data, field_types)
    required_validator(post_data, required_fields)
    email_validator(post_data["email"])

    firstname = post_data.get('firstname')
    lastname = post_data.get('lastname')
    email = post_data.get('email')
    password = post_data.get('password')
    gender = post_data.get("gender")
    profile_pic = post_data.get("profile_pic")

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            new_user = User(
                firstname=firstname,
                lastname=lastname,
                email=email,
                password=password
            )

            new_user.gender = gender
            new_user.profile_pic = profile_pic

            new_user.insert()

            auth_token = new_user.encode_auth_token(new_user.id)
            response_object = {
                'status': 'success',
                'message': 'User registered successfully.',
                'auth_token': auth_token.decode(),
                'id': new_user.id
            }
            return jsonify(response_object), 201
        else:
            response_object['message'] = 'Email already exists.'
            return jsonify(response_object), 400

    except Exception as e:
        logging.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 500