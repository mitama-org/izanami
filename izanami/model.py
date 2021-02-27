from mitama.db import BaseDatabase
from mitama.db.types import *
import git


class Database(BaseDatabase):
    pass


db = Database()

class Repo(db.Model):
    name = Column(String, primary_key=True, unique=True)
    owner = Column(Node, nullable=False)
    @property
    def entity(self):
        entity = git.Repo(
            self.project_dir / 'repos/{}.git'.format(self.name),
        )
        return entity


db.create_all()
