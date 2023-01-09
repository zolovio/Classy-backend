import datetime
from project import db
from project.models.user_model import User, Location
from project.models.sku_model import Campaign, Sku_Images, Sku_Stock, Coupon


class Order(db.Model):
    """
    Order Model:
    - id: int
    - status: str

    - total_quantity: int
    - total_tax: float
    - shipping_fee: float
    - total_amount: float

    - booking_date: datetime

    - user_id: int
    - location_id: int

    """
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status = db.Column(db.String(20), nullable=False, default="pending")

    total_quantity = db.Column(db.Integer, nullable=False, default=0)
    total_tax = db.Column(db.Float, nullable=False, default=0.0)
    shipping_fee = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)

    booking_date = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(
        'location.id'), nullable=False)

    def __init__(self, user_id: int, location_id: int, total_quantity: int,
                 total_tax: float, shipping_fee: float, total_amount: float, booking_date: str):
        self.user_id = user_id
        self.location_id = location_id
        self.total_quantity = total_quantity
        self.total_tax = total_tax
        self.shipping_fee = shipping_fee
        self.total_amount = total_amount
        self.booking_date = booking_date

    def __repr__(self):
        return f"Order {self.id} {self.status} {self.total_quantity} {self.total_tax} {self.shipping_fee} {self.total_amount} {self.booking_date} {self.user_id} {self.location_id}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        user = User.query.get(self.user_id)
        location = Location.query.get(self.location_id)

        return {
            "id": self.id,
            "user": user.to_json(),
            "status": self.status,
            "location": location.to_json() if location else None,
            "booking_date": self.booking_date.strftime("%Y-%m-%d") if self.booking_date else None,
            "total_tax": self.total_tax,
            "shipping_fee": self.shipping_fee,
            "total_amount": self.total_amount,
            "total_quantity": self.total_quantity
        }


class Order_Sku(db.Model):
    """
    Order_Sku Model:
    - id: int
    - order_id: int
    - quantity: int
    - total_price: float
    - sales_tax: float

    - coupon_id: int
    - campaign_id: int
    - sku_stock_id: int
    - sku_images_id: int
    """

    __tablename__ = 'order_sku'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    sales_tax = db.Column(db.Float, nullable=False, default=0.0)
    total_price = db.Column(db.Float, nullable=False, default=0.0)

    order_id = db.Column(db.Integer, db.ForeignKey(
        'order.id'), nullable=False)
    coupon_id = db.Column(db.Integer, db.ForeignKey(
        'coupon.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey(
        'campaign.id'), nullable=False)
    sku_stock_id = db.Column(db.Integer, db.ForeignKey(
        'sku_stock.id'), nullable=False)
    sku_images_id = db.Column(db.Integer, db.ForeignKey(
        'sku_images.id'), nullable=False)

    def __init__(self, order_id: int, quantity: int, total_price: float, sales_tax: float,
                 coupon_id: int, campaign_id: int, sku_stock_id: int, sku_images_id: int):
        self.order_id = order_id
        self.quantity = quantity
        self.total_price = total_price
        self.sales_tax = sales_tax
        self.coupon_id = coupon_id
        self.campaign_id = campaign_id
        self.sku_stock_id = sku_stock_id
        self.sku_images_id = sku_images_id

    def __repr__(self):
        return f"Order_Sku {self.id} {self.order_id} {self.quantity} {self.total_price} {self.sales_tax} {self.coupon_id} {self.campaign_id} {self.sku_stock_id} {self.sku_images_id}"

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
        campaign.pop('user')
        campaign['sku'].pop('sku_images')
        campaign['sku'].pop('sku_stock')

        campaign['sku']['sku_stock'] = Sku_Stock.query.get(
            self.sku_stock_id).to_json()
        campaign['sku']['sku_image'] = Sku_Images.query.get(
            self.sku_images_id).to_json()

        return {
            "id": self.id,
            "order_id": self.order_id,
            "quantity": self.quantity,
            "total_price": self.total_price,
            "sales_tax": self.sales_tax,
            "coupon": Coupon.query.get(self.coupon_id).to_json(),
            "campaign": campaign
        }
