from click import group, option

from .Server import Server, DEFAULT_PORT


@group()
def main():
    pass


@main.command()
@option('--port', '-p', type = int, default = DEFAULT_PORT)
@option('--callback', '-c', is_flag = True)
@option('--disabled-thread-starters', type = str, default = None)
def serve(port: int, callback: bool, disabled_thread_starters: str):
    Server(callback = callback, disabled_thread_starters = disabled_thread_starters).serve(port = port)


if __name__ == '__main__':
    main()
