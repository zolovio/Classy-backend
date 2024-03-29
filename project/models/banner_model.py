from project import db


class Banners(db.Model):
    """
    Banners Model:
        - id: int
        - user_id: int
        - image (url): str
        - title: str
        - subtitle: str
        - is_active: bool
    """
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    image = db.Column(db.String(128), nullable=False)
    title = db.Column(db.String(128), nullable=True, default="")
    subtitle = db.Column(db.String(128), nullable=True, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"Banners {self.id} {self.image} {self.is_active}"

    def __init__(self, user_id: int, image: str, title: str,
                 subtitle: str, is_active: bool = True):

        self.user_id = user_id
        self.image = image
        self.is_active = is_active
        self.title = title
        self.subtitle = subtitle

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
            "image": self.image,
            "title": self.title,
            "subtitle": self.subtitle,
            "is_active": self.is_active
        }
