from mitama.app import App, Router
from mitama.utils.controllers import static_files
from mitama.utils.middlewares import BasicMiddleware, SessionMiddleware, CsrfMiddleware
from mitama.app.method import view

#from .controller import RepoController, ProxyController, HookController
from .controller import RepoController, ProxyController, HookController, MergeController, SettingController
from .model import Repo, Merge, InnerPermission


class App(App):
    name = 'Izanami'
    description = 'Git server for Mitama.'
    merge = [Repo, Merge]
    router = Router(
        [
            view("/static/<path:path>", static_files()),
            Router([
                view("/<repo:re:(.*)\.git><path:path>", ProxyController),
            ], middlewares = [BasicMiddleware]),
            Router([
                view("/", RepoController),
                view("/create", RepoController, 'create'),
                view("/settings", SettingController),
                view("/<repo>", RepoController, 'retrieve'),
                view("/<repo>/update", RepoController, 'update'),
                view("/<repo>/delete", RepoController, 'delete'),
                view("/<repo>/tree/<head>", RepoController, 'retrieve'),
                view("/<repo>/blob/<head>/<object>", RepoController, 'blob'),
                view("/<repo>/commit/<commit>", RepoController, 'commit'),
                view("/<repo>/log", RepoController, 'log'),
                view("/<repo>/log/<head>", RepoController, 'log'),
                view("/<repo>/merge", MergeController),
                view("/<repo>/merge/create", MergeController, 'create'),
                view("/<repo>/merge/<merge>", MergeController, 'retrieve'),
                view("/<repo>/hook", HookController),
                view("/<repo>/hook/create", HookController, 'create'),
                view("/<repo>/hook/<hook>", HookController, 'retrieve'),
                view("/<repo>/hook/<hook>/edit", HookController, 'update'),
                view("/<repo>/hook/<hook>/delete", HookController, 'delete'),
            ], middlewares = [SessionMiddleware, CsrfMiddleware])
        ]
    )

    def init_app(self):
        Repo.project_dir = self.project_dir

    @property
    def view(self):
        view = super().view
        view.globals.update(
            permission=InnerPermission.is_accepted,
        )
        return view
