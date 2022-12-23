import jwt
import datetime
from flask import current_app

from project import db, bcrypt

"""
    Create Models
"""
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firstname = db.Column(db.String(128), nullable=False)
    lastname = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    mobile_no = db.Column(db.String(128), unique=True, nullable=True)
    password = db.Column(db.String(255), unique=True, nullable=False)
    profile_picture = db.Column(db.String(128), default="", nullable=True)

    active = db.Column(db.Boolean, default=True, nullable=False)
    account_suspension = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    location = db.relationship("Location", cascade="all, delete-orphan", backref=db.backref("user"))

    def __repr__(self):
        return f"User {self.id} {self.username}"

    def __init__(self, firstname:str, lastname:str, email:str, mobile_no:str, password:str, is_admin=False):
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.mobile_no = mobile_no
        self.password = bcrypt.generate_password_hash(password, current_app.config.get("BCRYPT_LOG_ROUNDS")).decode()
        self.is_admin = is_admin

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "email": self.email,
            "mobile_no": self.mobile_no,
            "profile_picture": self.profile_picture
            }

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token - :param user_id: - :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(
                    days=current_app.config.get('TOKEN_EXPIRATION_DAYS'),
                    seconds=current_app.config.get('TOKEN_EXPIRATION_SECONDS')
                ),
                'iat': datetime.datetime.utcnow(),
                'sub': user_id
            }
            return jwt.encode(
                payload,
                current_app.config.get('SECRET_KEY'),
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token - :param auth_token: - :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, current_app.config.get('SECRET_KEY'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'


class Location(db.Model):
    __tablename__ = "location"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    address = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(128), nullable=False)
    state = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(128), nullable=False)
    zipcode = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"Location {self.id} {self.address}"
    
    def __init__(self, address:str, city:str, state:str, country:str, zipcode:str, user_id:int):
        self.address = address
        self.city = city
        self.state = state
        self.country = country
        self.zipcode = zipcode
        self.user_id = user_id
    
    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.id,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zipcode": self.zipcode,
            "user_id": self.user_id
        }
        
class BlacklistToken(db.Model):
    """
    Token Model for storing JWT tokens
    """
    __tablename__ = 'blacklist_tokens'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return '<id: token: {}'.format(self.token)

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def check_blacklist(auth_token):
        # check whether auth token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(auth_token)).first()
        return True if res else False

    @staticmethod
    def get_all_blacklisted_tokens():
        return BlacklistToken.query.all()

    @staticmethod
    def delete_blacklisted_token(token):
        try:
            # get the token
            blacklist_token = BlacklistToken.query.filter_by(token=token).first()
            # delete the token
            blacklist_token.delete()
            return {
                'status': 'success',
                'message': 'Successfully logged out.'
            }
        except Exception as e:
            return e