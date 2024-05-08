from click import group, option

from .Server import Server, DEFAULT_PORT


@group()
def main():
    pass


@main.command()
@option('--port', '-p', type = int, default = DEFAULT_PORT)
@option('--callback', '-c', is_flag = True)
def serve(port: int, callback: bool):
    Server(callback = callback).serve(port = port)


if __name__ == '__main__':
    main()
