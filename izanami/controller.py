from mitama.app import Controller
from mitama.app.http import Response
from mitama.models import User, Group, InnerRole, Node, is_admin
from .model import Repo, Merge, InnerPermission
from .forms import MergeCreateForm, SettingsForm, HookCreateForm
from . import gitHttpBackend

import git
import os
import glob
import shutil
import yaml
import traceback
from io import StringIO
from unidiff import PatchSet


class RepoController(Controller):
    def handle(self, request):
        template = self.view.get_template("repo/list.html")
        repos = Repo.list()
        return Response.render(template, {
            'repos': repos
        })
    def create(self, request):
        template = self.view.get_template("repo/create.html")
        nodes = [
            *Group.list(),
            *User.list()
        ]
        try:
            if request.method == 'POST':
                body = request.post()
                repo = Repo()
                repo.name = body['name']
                repo.owner = Node.retrieve(body['owner'])
                repo.create()
                if not (self.app.project_dir / 'git_template').is_dir:
                    git.Repo.init(
                        self.app.project_dir / 'git_template',
                        bare = True
                    )
                git.Repo.init(
                    self.app.project_dir / ('repos/' + repo.name + '.git'),
                    bare = True,
                    template = self.app.project_dir / 'git_template'
                )
                return Response.redirect(self.app.convert_url('/'+repo.name))
        except Exception as err:
            error = str(err)
            traceback.print_exc(err)
            return Response.render(template, {
                'post': body,
                'error': error,
                'nodes': nodes
            })
        return Response.render(template, {
            'post': dict(),
            'nodes': nodes
        })

    def update(self, request):
        template = self.view.get_template("repo/update.html")
        repo = Repo.retrieve(name = request.params['repo'])
        if isinstance(repo.owner.object, Group) and not InnerPermission.is_accepted('update_repository', repo.owner.object, request.user):
            return Response.redirect(self.app.convert_url('/'))
        try:
            if request.method == 'POST':
                body = request.post()
                name = repo.name
                repo.name = body['name']
                repo.owner = Node(body['owner'])
                repo.update()
                os.rename(
                    self.app.project_dir / ('repos/' + name + '.git'),
                    self.app.project_dir / ('repos/' + repo.name + '.git')
                )
        except Exception as err:
            error = str(err)
            return Response.render(template, {
                'repo': repo,
                'error': error
            })
        return Response.render(template, {
            'repo': repo
        })

    def delete(self, request):
        template = self.view.get_template("repo/delete.html")
        repo = Repo.retrieve(name = request.params['repo'])
        if isinstance(repo.owner.object, Group) and not InnerPermission.is_accepted('delete_repository', repo.owner.object, request.user):
            return Response.redirect(self.app.convert_url('/'))
        try:
            if request.method == 'POST':
                if not request.user.password_check(request.post()['password']):
                    raise AuthorizationError('wrong password')
                shutil.rmtree(self.app.project_dir / ('repos/' + repo.name + '.git'))
                repo.delete()
                return Response.redirect(self.app.convert_url('/'))
        except Exception as err:
            error = str(err)
            return Response.render(template, {
                'repo': repo,
                'error': error
            })
        return Response.render(template, {
            'repo': repo
        })

    def retrieve(self, request):
        template = self.view.get_template("repo/retrieve.html")
        repo = Repo.retrieve(name = request.params['repo'])
        query = request.query
        current_head = request.params.get('head', 'master')
        entity = git.Repo(
            self.app.project_dir / 'repos/{}.git'.format(repo.name),
        )
        head = getattr(entity.heads, current_head) if hasattr(entity.heads, current_head) else None
        commit = None
        tree = None
        readme = None
        if head:
            commit = head.commit
            if commit:
                tree = commit.tree
                if tree:
                    for blob in tree:
                        if blob.name.startswith('README'):
                            readme = blob.data_stream.read().decode('utf-8')
        return Response.render(template, {
            'repo': repo,
            'current_head': current_head,
            'head': head,
            'tree': tree,
            'entity': entity,
            'readme': readme
        })

    def blob(self, request):
        template = self.view.get_template("repo/blob.html")
        repo = Repo.retrieve(name = request.params['repo'])
        query = request.query
        branch = query.get('branch', 'master')
        entity = git.Repo(
            self.app.project_dir / 'repos/{}.git'.format(repo.name),
        )
        head = getattr(entity.heads, branch) if hasattr(entity.heads, branch) else None
        tree = head.commit.tree or None
        content = None
        for obj in tree:
            if obj.name == request.params['object']:
                content = obj.data_stream.read().decode("utf-8")
        return Response.render(template, {
            'repo': repo,
            'branch': branch,
            'head': head,
            'tree': tree,
            'entity': entity,
            'name': request.params['object'],
            'content': content
        })

    def commit(self, request):
        template = self.view.get_template("repo/commit.html")
        repo = Repo.retrieve(name = request.params['repo'])
        query = request.query
        entity = repo.entity
        commit = entity.commit(request.params['commit'])
        diff_str = entity.git.diff(str(commit) + '~1', commit, ignore_blank_lines=True, ignore_space_at_eol=True) if len(commit.parents) > 0 else None
        diff = None
        if diff_str:
            diff = PatchSet(diff_str)
            for patch in diff:
                for hunk in patch:
                    print(dir(hunk))
        return Response.render(template, {
            'repo': repo,
            'entity': entity,
            'commit': commit,
            'diff': diff
        })

    def log(self, request):
        template = self.view.get_template("repo/log.html")
        repo = Repo.retrieve(name = request.params['repo'])
        current_head = request.params.get('head', 'master')
        query = request.query
        commits = repo.entity.iter_commits(current_head) if hasattr(repo.entity.heads, current_head) else None
        return Response.render(template, {
            'repo': repo,
            'entity': repo.entity,
            'current_head': current_head,
            'commits': commits
        })

class HookController(Controller):
    def handle(self, request):
        template = self.view.get_template('hook/list.html')
        repo = Repo.retrieve(name = request.params['repo'])
        hooks = list()
        for hook in glob.glob(str(self.app.project_dir / 'repos/{}.git/hooks'.format(repo.name)) + '/*'):
            hooks.append(os.path.basename(hook))
        return Response.render(template, {
            'repo': repo,
            'hooks': hooks
        })
    def retrieve(self, request):
        template = self.view.get_template('hook/retrieve.html')
        repo = Repo.retrieve(name = request.params['repo'])
        with open(self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, request.params['hook'])) as f:
            code = f.read()
        return Response.render(template, {
            'repo': repo,
            'name': request.params['hook'],
            'code': code
        })
    def create(self, request):
        template = self.view.get_template('hook/create.html')
        repo = Repo.retrieve(name = request.params['repo'])
        if isinstance(repo.owner.object, Group) and not InnerPermission.is_accepted('update_repository', repo.owner.object, request.user):
            return Response.redirect(self.app.convert_url('/' + request.params['repo'] + '/hook'))
        error = ''
        if request.method == 'POST':
            form = HookCreateForm(request.post())
            with open(self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, form['name']), 'w') as f:
                f.write(form['code'])
            return Response.redirect(self.app.convert_url('/{}/hook/{}'.format(repo.name, form['name'])))
        return Response.render(template, {
            'repo': repo,
            'error': error
        })
    def update(self, request):
        template = self.view.get_template('hook/update.html')
        repo = Repo.retrieve(name = request.params['repo'])
        if isinstance(repo.owner.object, Group) and not InnerPermission.is_accepted('update_repository', repo.owner.object, request.user):
            return Response.redirect(self.app.convert_url('/' + request.params['repo'] + '/hook'))
        error = ''
        if request.method == 'POST':
            form = HookCreateForm(request.post())
            shutil.move(
                self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, request.params['hook']),
                self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, form['name'])
            )
            with open(self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, form['name']), 'w') as f:
                f.write(form['code'])
            return Response.redirect(self.app.convert_url('/{}/hook/{}'.format(repo.name, form['name'])))
        with open(self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, request.params['hook'])) as f:
            code = f.read()
        return Response.render(template, {
            'repo': repo,
            'name': request.params['hook'],
            'code': code,
            'error': error
        })
    def delete(self, request):
        template = self.view.get_template('hook/delete.html')
        repo = Repo.retrieve(name = request.params['repo'])
        if isinstance(repo.owner.object, Group) and not InnerPermission.is_accepted('update_repository', repo.owner.object, request.user):
            return Response.redirect(self.app.convert_url('/' + request.params['repo'] + '/hook'))
        error = ''
        if request.method == 'POST':
            os.remove(self.app.project_dir / 'repos/{}.git/hooks/{}'.format(repo.name, request.params['hook']))
            return Response.redirect(self.app.convert_url('/{}/hook'.format(repo.name)))
        return Response.render(template, {
            'repo': repo,
            'name': request.params['hook'],
            'error': error
        })

class MergeController(Controller):
    def handle(self, request):
        template = self.view.get_template('merge/list.html')
        repo = Repo.retrieve(name = request.params['repo'])
        merges = Merge.query.filter(Merge.repo == repo).all()
        return Response.render(template, {
            "repo": repo,
            "merges": merges
        })

    def create(self, request):
        template = self.view.get_template('merge/create.html')
        repo = Repo.retrieve(name = request.params['repo'])
        error = ""
        if request.method == "POST":
            try:
                form = MergeCreateForm(request.post())
                merge = Merge()
                merge.base = form['base']
                merge.compare = form['compare']
                merge.title = form['title']
                merge.body = form['body']
                merge.repo = repo
                merge.user = request.user
                merge.create()
                return Response.redirect(self.app.convert_url('/' + repo.name + '/merge/' + merge._id))
            except Exception as err:
                error = str(err)
        return Response.render(template, {
            "repo": repo,
            "entity": repo.entity,
            "error": error
        })

    def retrieve(self, request):
        template = self.view.get_template('merge/retrieve.html')
        repo = Repo.retrieve(name = request.params['repo'])
        merge = Merge.retrieve(request.params['merge'])
        if request.method == 'POST':
            post = request.post()
            if post['action'] == 'merge':
                merge.merge()
                merge.delete()
            else:
                merge.delete()
            return Response.redirect(self.app.convert_url('/' + repo.name))
        return Response.render(template, {
            "repo": repo,
            "entity": repo.entity,
            "merge": merge
        })

class ProxyController(Controller):
    def handle(self, request):
        repo = Repo.retrieve(name = request.params['repo'][:-4])
        if repo.owner.object._id != request.user._id and (isinstance(repo.owner, Group) and not repo.owner.object.is_in(request.user)):
            return Response(status=401, reason='Unauthorized', text='You are not the owner of the repository.')
        environ = dict(request.environ)
        environ['REQUEST_METHOD'] = request.method
        environ['PATH_INFO'] = self.app.revert_url(environ['PATH_INFO'])
        (
            status,
            reason,
            headers,
            body
        ) = gitHttpBackend.wsgi_to_git_http_backend(environ, self.app.project_dir / 'repos')
        content_type = headers['Content-Type']
        return Response(
            body = body,
            status = status,
            reason = reason,
            headers = headers,
            content_type = content_type
        )

class SettingController(Controller):
    def handle(self, request):
        if not is_admin(request.user):
            return Response.redirect(self.app.convert_url('/'))
        error = ""
        if request.method == "POST":
            try:
                form = SettingsForm(request.post())
                for permission_screen_name, permission_roles in form['permission'].items():
                    permission = InnerPermission.retrieve(screen_name = permission_screen_name)
                    permission.roles = [InnerRole.retrieve(screen_name = role) for role in permission_roles]
                    permission.update()
                error = "変更を保存しました"
            except Exception as err:
                error = str(err)
        template = self.view.get_template('settings.html')
        return Response.render(template, {
            "roles": InnerRole.list(),
            "permissions": InnerPermission.list(),
            "error": error
        })


