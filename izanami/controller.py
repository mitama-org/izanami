from mitama.app import Controller
from mitama.app.http import Response
from mitama.models import User, Group
from .model import Repo
from . import gitHttpBackend

import git
import os
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
                git.Repo.init(
                    self.app.project_dir / ('repos/' + repo.name + '.git'),
                    bare = True
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
        return Response.render(template, {
            'repo': repo
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
