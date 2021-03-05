from mitama.db import BaseDatabase, relationship
from mitama.db.types import *
from mitama.models import inner_permission, Role, User, Node
import git
import hashlib
import shutil
import asyncio


class Database(BaseDatabase):
    pass


db = Database(prefix="izanami")

class Repo(db.Model):
    name = Column(String(64), primary_key=True, unique=True)
    owner = relationship(Node)
    owner_id = Column(String(64), ForeignKey("mitama_node._id"))
    @property
    def entity(self):
        entity = git.Repo(
            self.project_dir / 'repos/{}.git'.format(self.name),
        )
        return entity
    def merge(self, source, target):
        dirname = hashlib.sha256()
        dirname.update(self.name.encode())
        dirname.update(source.encode())
        dirname.update(target.encode())
        dirname = dirname.hexdigest()
        repo = git.Repo.clone_from(
            self.project_dir / 'repos/{}.git'.format(self.name),
            self.project_dir / 'tmp/{}'.format(dirname),
            branch=source
        )
        repo.index.merge_tree('origin/' + target).commit("Merged into {}".format(source))
        repo.remotes.origin.push()
        shutil.rmtree(self.project_dir / 'tmp/{}'.format(dirname))

class Merge(db.Model):
    repo_id = Column(String(64), ForeignKey("izanami_repo._id"))
    repo = relationship(Repo)
    base = Column(String(255), nullable=False)
    compare = Column(String(255), nullable=False)
    body = Column(String(1000))
    title = Column(String(255))
    user_id = Column(String(64), ForeignKey("mitama_user._id"))
    user = relationship(User)
    @property
    def meta(self):
        md = markdown.Metadata(extensions=["meta"])
        data = md.convert(self.body)
        return data.Meta

    def merge(self):
        self.repo.merge(self.base, self.compare)
        self.on("merge")()

Merge.listen("merge")

InnerPermission = inner_permission(db, [
    {
        "name": "ブランチのマージ",
        "screen_name": "merge"
    },
    {
        "name": "masterへのpush",
        "screen_name": "push_master",
    },
    {
        "name": "developへのpush",
        "screen_name": "push_develop",
    },
    {
        "name": "その他ブランチへのpush",
        "screen_name": "push_other",
    },
    {
        "name": "リポジトリの作成",
        "screen_name": "create_repository"
    },
    {
        "name": "リポジトリの削除",
        "screen_name": "delete_repository"
    },
    {
        "name": "リポジトリの設定",
        "screen_name": "update_repository"
    }
])

db.create_all()
