"""Run the installed formal CLI with outbound Python socket access denied."""
import sys


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("offline_acceptance_network_access_denied")


sys.addaudithook(deny_network)
from hakimi_research.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
