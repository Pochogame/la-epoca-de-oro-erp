from app import create_app
from app.extensions import db
from app.seed import seed_database

app = create_app()

with app.app_context():
    seed_database(reset=True)
    print("Base de datos reiniciada y sembrada correctamente.")
