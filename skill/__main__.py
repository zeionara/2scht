from click import group, option

from .Server import Server, DEFAULT_PORT


@group()
def main():
    pass


@main.command()
@option('--port', '-p', type = int, default = DEFAULT_PORT)
def serve(port: int):
    Server().serve(port = port)


if __name__ == '__main__':
    main()
