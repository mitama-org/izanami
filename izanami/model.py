from mitama.db import BaseDatabase, relationship
from mitama.db.types import *
import git
import hashlib
import shutil


class Database(BaseDatabase):
    pass


db = Database(prefix="izanami")

class Repo(db.Model):
    name = Column(String(64), primary_key=True, unique=True)
    owner = Column(Node, nullable=False)
    @property
    def entity(self):
        entity = git.Repo(
            self.project_dir / 'repos/{}.git'.format(self.name),
        )
        return entity
    def merge(self, source, target):
        dirname = hashlib.sha256()
        dirname.update(self.name.encode())
        dirname.update(self.source.encode())
        dirname.update(self.target.encode())
        dirname = dirname.hexdigest()
        repo = git.Repo.clone_from(
            self.project_dir / 'repos/{}.git'.format(self.name),
            self.project_dir / 'tmp/{}'.format(dirname),
        )
        repo.heads[source].checkout()
        repo.index.merge_tree(target).commit("Merged into {}".format(self.base))
        repo.remotes.origin.push()
        shutil.rmtree(self.project_dir / 'tmp/{}'.format(dirname))

class Merge(db.Model):
    repo_id = Column(String(64), ForeignKey("izanami_repo._id"))
    repo = relationship(Repo)
    base = Column(String(64), nullable=False)
    compare = Column(String(64), nullable=False)
    body = Column(String(64))
    title = Column(String(64))
    @property
    def meta(self):
        md = markdown.Metadata(extensions=["meta"])
        data = md.convert(self.body)
        return data.Meta

    def merge(self):
        self.repo.merge(base, compare)
        self.on("merge")(self)

db.create_all()
