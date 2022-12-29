import datetime
from project import db
from project.models.user_model import User


class Sku(db.Model):
    """
    Sku Model:
        - id: int
        - user_id: int

        - name: str
        - description: str
        - category: str

        - price: float

        - quantity: int
        - number_sold: int
        - number_delivered: int

        - size_chart (url): str

        - Sku_Images (Model)
        - Sku_Stock (Model)
        - Campaign (Model)
        - Prize (Model)
        - Draw (Model)
    """

    __tablename__ = "sku"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(128), nullable=False)

    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    number_sold = db.Column(db.Integer, nullable=False)
    number_delivered = db.Column(db.Integer, nullable=False)

    size_chart = db.Column(db.String(256), nullable=False)

    sku_images = db.relationship(
        "Sku_Images", cascade="all, delete-orphan", backref=db.backref("sku"))
    sku_stock = db.relationship(
        "Sku_Stock", cascade="all, delete-orphan", backref=db.backref("sku"))

    def __repr__(self):
        return f"SKU {self.id} {self.name}"

    def __init__(self, name: str, description: str, category: str,
                 price: float, quantity: int, size_chart: str,
                 number_sold: int, number_delivered: int,  user_id: int):

        self.name = name
        self.description = description
        self.category = category
        self.price = price
        self.quantity = quantity
        self.size_chart = size_chart
        self.number_sold = number_sold
        self.number_delivered = number_delivered

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
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "price": self.price,
            "quantity": self.quantity,
            "number_sold": self.number_sold,
            "number_delivered": self.number_delivered,
            "size_chart": self.size_chart,
            "sku_images": [image.to_json() for image in Sku_Images.query.filter_by(sku_id=self.id).all()],
            "sku_stock": [stock.to_json() for stock in Sku_Stock.query.filter_by(sku_id=self.id).all()],
        }


class Sku_Images(db.Model):
    """
    Sku_Images Model:
        - id: int
        - image (url): str
        - sku_id: int

    """
    __tablename__ = "sku_images"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku_id = db.Column(db.Integer, db.ForeignKey("sku.id"), nullable=False)
    image = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f"Sku_Images {self.id} {self.image}"

    def __init__(self, image: str, sku_id: int):
        self.image = image
        self.sku_id = sku_id

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
            "image": self.image,
            "sku_id": self.sku_id
        }


class Sku_Stock(db.Model):
    """
    Sku_Stock Model
        - id: int
        - size: str
        - stock: int
        - color: str
        - sku_id: int
    """
    __tablename__ = "sku_stock"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku_id = db.Column(db.Integer, db.ForeignKey("sku.id"), nullable=False)
    size = db.Column(db.String(128), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"Sku_Stock {self.id} {self.size} {self.stock} {self.color}"

    def __init__(self, size: str, stock: int, color: str, sku_id: int):
        self.size = size
        self.stock = stock
        self.color = color
        self.sku_id = sku_id

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
            "size": self.size,
            "stock": self.stock,
            "color": self.color,
            "sku_id": self.sku_id
        }


class Prize(db.Model):
    """
    Prize Model:
        - id: int
        - user_id: int

        - name: str
        - description: str
        - image (url): str

    """
    __tablename__ = "prize"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(128), nullable=False)
    image = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"Prize {self.id} {self.name}"

    def __init__(self, name: str, description: str, image: str, user_id: int):
        self.name = name
        self.description = description
        self.image = image
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
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "image": self.image
        }


class Campaign(db.Model):
    """
    Campaign Model:
        - id: int
        - user_id: int

        - name: str
        - description: str
        - image (url): str
        - threshold: int

        - start_date: datetime
        - end_date: datetime

        - is_active: bool

        - sku_id: int
        - prize_id: int

    """

    __tablename__ = "campaign"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sku_id = db.Column(db.Integer, db.ForeignKey("sku.id"), nullable=False)
    prize_id = db.Column(db.Integer, db.ForeignKey("prize.id"), nullable=False)

    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(128), nullable=False)
    image = db.Column(db.String(128), nullable=False)
    threshold = db.Column(db.Integer, nullable=False)

    is_active = db.Column(db.Boolean, nullable=False, default=False)

    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)

    sku = db.relationship(
        "Sku", cascade="all, delete-orphan", single_parent=True, backref=db.backref("campaign"))
    prize = db.relationship(
        "Prize", cascade="all, delete-orphan", single_parent=True, backref=db.backref("campaign"))

    def __repr__(self):
        return f"Campaign {self.id} {self.name}"

    def __init__(self, user_id: int, sku_id: int, prize_id: int, threshold: int,
                 name: str, description: str, image: str,
                 start_date: str, end_date: str):

        self.name = name
        self.description = description
        self.image = image
        self.threshold = threshold

        self.start_date = start_date
        self.end_date = end_date

        self.user_id = user_id
        self.sku_id = sku_id
        self.prize_id = prize_id

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
            "user": User.query.get(self.user_id).to_json(),
            "sku": Sku.query.get(self.sku_id).to_json(),
            "prize": Prize.query.get(self.prize_id).to_json(),
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "threshold": self.threshold,
            "is_active": self.is_active,
            "start_date": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "end_date": self.end_date.strftime("%Y-%m-%d") if self.end_date else None
        }


class Coupon(db.Model):
    """
    Coupon Model:
        - id: int
        - user_id: int
        - campaign_id: int
        - sku_images_id: int
        - sku_stock_id: int

        - code: str
        - datetime: datetime
        - is_active: bool

    """
    __tablename__ = "coupon"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey(
        "campaign.id"), nullable=False)
    sku_images_id = db.Column(db.Integer, db.ForeignKey(
        "sku_images.id"), nullable=False)
    sku_stock_id = db.Column(db.Integer, db.ForeignKey(
        "sku_stock.id"), nullable=False)

    code = db.Column(db.String(128), unique=True, nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"Coupon {self.id} {self.code}"

    def __init__(self, user_id: int, campaign_id: int, sku_images_id: int,
                 sku_stock_id: int, datetime: str, amount_paid: float):

        self.user_id = user_id
        self.campaign_id = campaign_id
        self.sku_images_id = sku_images_id
        self.sku_stock_id = sku_stock_id
        self.datetime = datetime
        self.amount_paid = amount_paid
        self.code = Coupon.generate_code(
            user_id, campaign_id, sku_stock_id, sku_images_id, datetime)

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
        campaign['sku'].pop('sku_images')
        campaign['sku'].pop('sku_stock')
        campaign.pop('user')

        return {
            "id": self.id,
            "sku_name": campaign['sku']['name'],
            "amount_paid": self.amount_paid,
            "sku_image": Sku_Images.query.get(self.sku_images_id).to_json(),
            "sku_stock": Sku_Stock.query.get(self.sku_stock_id).to_json(),
            "coupon_code": self.code,
            "is_active": self.is_active,
            "purchased on": self.datetime.strftime("%d %b, %Y %I:%M%p")
        }

    @staticmethod
    def generate_code(user_id: int, campaign_id: int, sku_stock_id: int, sku_images_id: int, datetime: datetime):
        upper_case_letters = [chr(i) for i in range(65, 91)]

        letters = upper_case_letters[campaign_id % 26] + \
            upper_case_letters[sku_stock_id % 26] + \
            upper_case_letters[sku_images_id % 26]

        digits = str(user_id) + str(campaign_id % 10) + \
            str(sku_images_id % 10) + str(sku_stock_id % 10)

        return f"{letters}-{digits}-{datetime.strftime('%m%d')}-{datetime.strftime('%M%S')}"
