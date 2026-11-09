"""
CorePulse v1.0 - Autonomous Productivity Engine & Life OS
Main entrypoint and zero-dependency production HTTP server.
"""

import argparse
import logging
import os
import signal
import sys
from http.server import ThreadingHTTPServer

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corepulse.api_handler import CorePulseRequestHandler
from corepulse.config import HOST, PORT, VERSION, APP_NAME, APP_TAGLINE, BUILD_ID

def setup_logging(debug: bool = False):
    """Configures structured console logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def print_banner(host: str, port: int):
    """Prints production startup ASCII banner and routing table."""
    border = "=" * 68
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    print(border)
    print(f"  [*] {APP_NAME} v{VERSION} ({BUILD_ID})")
    print(f"      {APP_TAGLINE}")
    print(border)
    print(f"  * Web Dashboard & Cockpit:  {url}/")
    print(f"  * API Health Check:         {url}/api/health")
    print(f"  * Tasks & Habits API:       {url}/api/tasks")
    print(f"  * Workflow Execution API:   {url}/api/workflows/run")
    print(f"  * Productivity Metrics API: {url}/api/metrics")
    print(f"  * Subscription & Tiers:     {url}/api/subscription")
    print(border)
    print("  [+] Server initialized with zero external dependencies.")
    print("  [+] Press Ctrl+C to initiate graceful shutdown.")
    print(border)

def run_server(host: str = HOST, port: int = PORT, debug: bool = False):
    """Runs CorePulse multi-threaded HTTP server."""
    setup_logging(debug)
    logger = logging.getLogger("corepulse.server")

    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, CorePulseRequestHandler)
        httpd.daemon_threads = True
    except OSError as e:
        logger.error(f"Failed to bind to {host}:{port}: {e}")
        print(f"\n[ERROR] Port {port} is unavailable. Try running with --port <alternative_port>.")
        sys.exit(1)

    print_banner(host, port)

    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received. Stopping CorePulse gracefully...")
        httpd.shutdown()
        logger.info("CorePulse stopped. Goodbye.")
        sys.exit(0)

    # Register OS signals
    try:
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
    except (ValueError, AttributeError):
        pass  # On Windows some signals may behave differently

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Stopping...")
    finally:
        httpd.server_close()
        logger.info("Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Server")
    parser.add_argument("--host", default=HOST, help=f"Host interface to bind (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port number to bind (default: {PORT})")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)
