from mitama.app import App, Router
from mitama.utils.controllers import static_files
from mitama.utils.middlewares import BasicMiddleware, SessionMiddleware, CsrfMiddleware
from mitama.app.method import view

from .controller import RepoController, ProxyController, HookController
from .model import Repo


class App(App):
    name = 'Izanami'
    description = 'Git server for Mitama.'
    router = Router(
        [
            view("/static/<path:path>", static_files()),
            Router([
                view("/<repo:re:(.*)\.git><path:path>", ProxyController),
            ], middlewares = [BasicMiddleware]),
            Router([
                view("/", RepoController),
                view("/create", RepoController, 'create'),
                view("/hook", HookController),
                view("/hook/create", HookController, 'create'),
                view("/hook/<hook>", HookController, 'retrieve'),
                view("/hook/<hook>/edit", HookController, 'update'),
                view("/hook/<hook>/delete", HookController, 'delete'),
                view("/<repo>", RepoController, 'retrieve'),
                view("/<repo>/hook", RepoController, 'hook_list'),
                view("/<repo>/hook/create", RepoController, 'hook_create'),
                view("/<repo>/hook/<hook>", RepoController, 'hook_retrieve'),
                view("/<repo>/hook/<hook>/edit", RepoController, 'hook_update'),
                view("/<repo>/hook/<hook>/delete", RepoController, 'hook_delete'),
                view("/<repo>/update", RepoController, 'update'),
                view("/<repo>/delete", RepoController, 'delete'),
                view("/<repo>/tree/<head>", RepoController, 'retrieve'),
                view("/<repo>/blob/<head>/<object>", RepoController, 'blob'),
                view("/<repo>/commit/<commit>", RepoController, 'commit'),
                view("/<repo>/log", RepoController, 'log'),
            ], middlewares = [SessionMiddleware, CsrfMiddleware])
        ]
    )

    def init_app(self):
        Repo.project_dir = self.project_dir
