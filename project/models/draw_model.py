import datetime
from project import db
from project.models.user_model import User
from project.models.sku_model import Campaign


class Draw(db.Model):
    """
    Draw Model:
    - id: int
    - video_url: string
    - start_date: datetime
    - end_date: datetime
    - winner_id: int
    - campaign_id: int
    """

    __tablename__ = 'draw'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_url = db.Column(db.String(128), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)

    campaign_id = db.Column(db.Integer,
                            db.ForeignKey('campaign.id'), nullable=False)
    winner_id = db.Column(db.Integer,
                          db.ForeignKey('user.id'), nullable=True)

    def __init__(self, campaign_id: int, video_url: str = None):
        self.campaign_id = campaign_id
        self.video_url = video_url

    def __repr__(self):
        return f"Draw {self.id} {self.start_date} {self.end_date} {self.winner_id} {self.campaign_id}"

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
        winner = User.query.get(self.winner_id).to_json()

        campaign.pop('user')
        campaign['sku'].pop('sku_images')
        campaign['sku'].pop('sku_stock')

        return {
            "id": self.id,
            "video_url": self.video_url,
            "start_date": self.start_date.strftime("%B %-d, %Y %I:%M%p") if self.start_date else None,
            "draw_date": self.end_date.strftime("%B %-d, %Y %I:%M%p") if self.end_date else None,
            "winner": winner,
            "campaign": campaign
        }
