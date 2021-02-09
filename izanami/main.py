from mitama.app import App, Router
from mitama.utils.controllers import static_files
from mitama.utils.middlewares import BasicMiddleware, SessionMiddleware
from mitama.app.method import view

from .controller import RepoController, ProxyController


class App(App):
    name = 'Izanami'
    description = 'Git server for Mitama.'
    router = Router(
        [
            Router([
                view("/<repo:re:(.*)\.git><path:path>", ProxyController),
            ], middlewares = [BasicMiddleware]),
            Router([
                view("/", RepoController),
                view("/create", RepoController, 'create'),
                view("/<repo>", RepoController, 'retrieve'),
                view("/<repo>/update", RepoController, 'update'),
                view("/<repo>/delete", RepoController, 'delete'),
                view("/static/<path:path>", static_files()),
            ], middlewares = [SessionMiddleware])
        ]
    )
