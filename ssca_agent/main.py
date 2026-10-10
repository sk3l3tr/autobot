import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

import argparse
from .ssca_server import SSCAServer

def main():
    print("[SSCA] Starting application ...")
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='SSCA host address')
    parser.add_argument('--port', type=int, help='SSCA port number')

    args = parser.parse_args()

    server = SSCAServer(
        host=args.host, 
        port=args.port
    )
    server.start()

if __name__ == "__main__" and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main();