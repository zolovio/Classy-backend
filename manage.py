from flask.cli import FlaskGroup

from project import create_app, db
from project.models.user_model import User

app = create_app()
cli = FlaskGroup(create_app=create_app)

@cli.command()
def recreate_db():
    db.drop_all()
    db.create_all()
    db.session.commit()

@cli.command()
def create_db():
    db.create_all()
    db.session.commit()
