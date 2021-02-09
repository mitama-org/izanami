from mitama.db import BaseDatabase
from mitama.db.types import *


class Database(BaseDatabase):
    pass


db = Database()

class Repo(db.Model):
    name = Column(String, primary_key=True, unique=True)
    owner = Column(Node, nullable=False)

db.create_all()
