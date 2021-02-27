from mitama.app import Controller
from mitama.app.http import Response
from mitama.models import User, Group
from .model import Repo
from .forms import HookUpdateForm, HookCreateForm
from . import gitHttpBackend

import git
import os
import glob
import shutil


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
                repo.owner = body['owner']
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
            print(error)
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
        try:
            if request.method == 'POST':
                body = request.post()
                name = repo.name
                repo.name = body['name']
                repo.owner = body['owner']
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
        tree = head.commit.tree or None
        return Response.render(template, {
            'repo': repo,
            'current_head': current_head,
            'head': head,
            'tree': tree,
            'entity': entity
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
            'obj': obj,
            'content': content
        })

    def commit(self, request):
        template = self.view.get_template("repo/commit.html")
        repo = Repo.retrieve(name = request.params['repo'])
        query = request.query
        entity = repo.entity
        commit = entity.commit(request.params['commit'])
        diff = commit.parents[0].diff(commit, create_patch=True) if len(commit.parents) > 0 else None

        return Response.render(template, {
            'repo': repo,
            'entity': entity,
            'commit': commit,
            'diff': diff
        })
    def log(self, request):
        template = self.view.get_template("repo/log.html")
        repo = Repo.retrieve(name = request.params['repo'])
        query = request.query
        return Response.render(template, {
            'repo': repo,
            'entity': repo.entity,
        })
    def hook_list(self, request):
        template = self.view.get_template("repo/hook_list.html")
        repo = Repo.retrieve(name = request.params['repo'])
        hooks = glob.glob(str(self.app.project_dir / 'repos/{}.git/hooks'.format(repo.name)) + '/*')
        return Response.render(template, {
            'hooks': [os.path.basename(hook) for hook in hooks],
            'repo': repo
        })
    def hook_retrieve(self, request):
        template = self.view.get_template("repo/hook_retrieve.html")
        repo = Repo.retrieve(name = request.params['repo'])
        with open(self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + request.params['hook'])) as f:
            content = f.read()
        return Response.render(template, {
            "hook": request.params["hook"],
            "repo": repo,
            "content": content
        })
    def hook_create(self, request):
        template = self.view.get_template("repo/hook_create.html")
        repo = Repo.retrieve(name = request.params['repo'])
        error = ''
        if request.method == "POST":
            post = request.post()
            try:
                form = HookCreateForm(post)
                name = form['name']
                content = form['code']
                with open(self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + name), 'w') as f:
                    f.write(content)
                return Response.redirect(self.app.convert_url(repo.name + '/hook/' + name))
            except Exception as err:
                error = str(err)
        return Response.render(template, {
            "repo": repo,
            "error": error,
        })
    def hook_update(self, request):
        template = self.view.get_template("repo/hook_update.html")
        repo = Repo.retrieve(name = request.params['repo'])
        with open(self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + request.params['hook'])) as f:
            content = f.read()
        error = ''
        if request.method == "POST":
            post = request.post()
            try:
                form = HookUpdateForm(post)
                name = form['name']
                content = form['code']
                shutil.move(
                    self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + request.params['hook']),
                    self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + name)
                )
                with open(self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + name), 'w') as f:
                    f.write(content)
                error = '保存しました'
                return Response.redirect(self.app.convert_url(request.params['repo'] + '/hook/' + name + '/edit'))
            except Exception as err:
                content = post.get('content', content)
                error = str(err)
        return Response.render(template, {
            "repo": repo,
            "hook": request.params["hook"],
            "content": content,
            "error": error
        })
    def hook_delete(self, request):
        template = self.view.get_template("repo/hook_delete.html")
        repo = Repo.retrieve(name = request.params['repo'])
        error = ''
        if request.method == "POST":
            try:
                os.remove(self.app.project_dir / ('repos/' + repo.name + '.git/hooks/' + request.params['hook']))
                return Response.redirect(self.app.convert_url(request.params['repo'] + '/hook'))
            except Exception as err:
                error = str(err)
        return Response.render(template, {
            "hook": request.params["hook"],
            "repo": repo,
            "error": error
        })

class HookController(Controller):
    def handle(self, request):
        template = self.view.get_template("hook/list.html")
        if not (self.app.project_dir / 'git_template').is_dir:
            git.Repo.init(
                self.app.project_dir / 'git_template',
                bare = True
            )
        hooks = glob.glob(str(self.app.project_dir / 'git_template/hooks') + '/*')
        return Response.render(template, {
            'hooks': [os.path.basename(hook) for hook in hooks]
        })
    def retrieve(self, request):
        template = self.view.get_template("hook/retrieve.html")
        with open(self.app.project_dir / ('git_template/hooks/' + request.params['hook'])) as f:
            content = f.read()
        return Response.render(template, {
            "hook": request.params["hook"],
            "content": content
        })
    def create(self, request):
        template = self.view.get_template("hook/create.html")
        error = ''
        if request.method == "POST":
            post = request.post()
            try:
                form = HookCreateForm(post)
                name = form['name']
                content = form['code']
                with open(self.app.project_dir / ('git_template/hooks/' + name), 'w') as f:
                    f.write(content)
                error = '保存しました'
                return Response.redirect(self.app.convert_url('/hook/' + name))
            except Exception as err:
                error = str(err)
        return Response.render(template, {
            "error": error
        })
    def update(self, request):
        template = self.view.get_template("hook/update.html")
        name = request.params['hook']
        with open(self.app.project_dir / ('git_template/hooks/' + name)) as f:
            content = f.read()
        error = ''
        if request.method == "POST":
            post = request.post()
            try:
                form = HookUpdateForm(post)
                name = form['name']
                content = form['code']
                shutil.move(
                    self.app.project_dir / ('git_template/hooks/' + request.params['hook']),
                    self.app.project_dir / ('git_template/hooks/' + name)
                )
                with open(self.app.project_dir / ('git_template/hooks/' + name), 'w') as f:
                    f.write(content)
                error = '保存しました'
                return Response.redirect(self.app.convert_url('/hook/' + name + '/edit'))
            except Exception as err:
                content = post.get('content', content)
                error = str(err)
        return Response.render(template, {
            "hook": name,
            "content": content,
            "error": error
        })
    def delete(self, request):
        template = self.view.get_template("hook/delete.html")
        error = ''
        if request.method == "POST":
            try:
                os.remove(self.app.project_dir / ('git_template/hooks/' + request.params['hook']))
                return Response.redirect(self.app.convert_url('/hook'))
            except Exception as err:
                error = str(err)
        return Response.render(template, {
            "hook": request.params['hook'],
            "error": error
        })


class ProxyController(Controller):
    def handle(self, request):
        repo = Repo.retrieve(name = request.params['repo'][:-4])
        if repo.owner._id != request.user._id and (isinstance(repo.owner, Group) and not repo.owner.is_in(request.user)):
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
