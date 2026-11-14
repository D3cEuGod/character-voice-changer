"""A fast connect probe must still allow normal HTTP response latency."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from gui.backend import BackendClient, BackendError, BackendLauncher


class DelayedHealth(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(.25)
        data=b'{"status":"ok","version":"test"}'
        self.send_response(200)
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self,*args):
        pass


class ProbeTests(unittest.TestCase):
    def test_closed_port_fails_quickly(self):
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1',0))
            client=BackendClient(f'http://127.0.0.1:{reserved.getsockname()[1]}')
            start=time.perf_counter()
            with self.assertRaises(BackendError):
                client.health(connect_timeout=.1)
            self.assertLess(time.perf_counter()-start,.8)

    def test_slow_http_response_is_not_mistaken_for_dead_backend(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),DelayedHealth)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            ready,failed=[],[]
            client=BackendClient(f'http://127.0.0.1:{server.server_port}')
            launcher=BackendLauncher(client,lambda _:None,lambda *args:ready.append(args),failed.append)
            launcher.run()
            self.assertEqual(failed,[])
            self.assertEqual(ready[0][0]['status'],'ok')
            self.assertFalse(ready[0][1])
            self.assertIsNone(launcher.process)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(2)


if __name__=='__main__':
    unittest.main(verbosity=2)
