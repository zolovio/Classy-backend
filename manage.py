from flask.cli import FlaskGroup

from project import create_app, db
from project.models.user_model import User, Location

app = create_app()
cli = FlaskGroup(create_app=create_app)


@cli.command()
def recreate_db():
    """Recreates a local database."""
    print("Recreating database...")
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command()
def create_db():
    """Creates a local database."""
    print("Creating database...")
    db.create_all()
    db.session.commit()


@cli.command()
def seed_db():
    """Seeds the database."""
    print("Seeding database...")

    admin = User(
        firstname="Super",
        lastname="Admin",
        email="admin@alphalive.com",
        mobile_no="1234567890",
        password="greaterthaneight",
        role="admin",
        is_admin=True
    )
    admin.profile_picture = "https://ik.imagekit.io/zol0vio/admin-user-icon_uOWwzefMA.jpg"
    admin.insert()

    Location(
        address="1234 Main Street",
        city="New York",
        state="NY",
        country="USA",
        zipcode="12345",
        user_id=admin.id
    ).insert()

    user = User(
        firstname="John",
        lastname="Doe",
        email="john.doe@alphalive.com",
        mobile_no="2234567890",
        password="greaterthaneight",
    )
    user.profile_picture = "https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png"
    user.insert()

    Location(
        address="1234 Main Boulevard",
        city="Manchester",
        state="NH",
        country="UK",
        zipcode="12345",
        user_id=user.id
    ).insert()

    print("Database seeded!")


if __name__ == "__main__":
    cli()
