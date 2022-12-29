import datetime
from project import db

from project.models.sku_model import Campaign, Sku_Stock, Sku_Images


class ShoppingCart(db.Model):
    __tablename__ = 'shopping_cart'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)
    checkedout_at = db.Column(db.DateTime, nullable=True, default=None)

    def __init__(self, user_id: int):
        self.user_id = user_id

    def __repr__(self):
        return f"ShoppingCart {self.id} {self.user_id}"

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
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else None,
            "checkedout_at": self.checkedout_at.strftime("%Y-%m-%d") if self.checkedout_at else None
        }


class CartItem(db.Model):
    __tablename__ = 'cart_item'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey(
        'shopping_cart.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey(
        'campaign.id'), nullable=False)
    sku_stock_id = db.Column(db.Integer, db.ForeignKey(
        'sku_stock.id'), nullable=False)
    sku_images_id = db.Column(db.Integer, db.ForeignKey(
        'sku_images.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)

    reservation_date = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __init__(self, cart_id: int, campaign_id: int, sku_stock_id: int, sku_images_id: int, quantity: int):
        self.cart_id = cart_id
        self.campaign_id = campaign_id
        self.sku_stock_id = sku_stock_id
        self.sku_images_id = sku_images_id
        self.quantity = quantity

    def __repr__(self):
        return f"CartItem {self.id} {self.cart_id} {self.campaign_id} {self.sku_stock_id} {self.sku_images_id} {self.quantity}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        campaign = Campaign.query.get(self.campaign_id).to_json()
        campaign['sku'].pop('sku_stock')
        campaign['sku'].pop('sku_images')
        campaign.pop('user')

        return {
            "id": self.id,
            "cart_id": self.cart_id,
            "campaign": campaign,
            "sku_stock": Sku_Stock.query.get(self.sku_stock_id).to_json(),
            "sku_images": Sku_Images.query.get(self.sku_images_id).to_json(),
            "quantity": self.quantity,
            "reservation_date": self.reservation_date.strftime("%Y-%m-%d") if self.reservation_date else None
        }
