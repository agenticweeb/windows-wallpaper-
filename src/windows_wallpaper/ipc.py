from __future__ import annotations

import json
import socket
import threading


class IPC:
    HOST = "127.0.0.1"
    PORT = 39741

    def send(self, command: str) -> bool:
        try:
            with socket.create_connection((self.HOST, self.PORT), timeout=0.4) as sock:
                sock.sendall(json.dumps({"command": command}).encode("utf-8"))
            return True
        except OSError:
            return False

    def listen(self, handler) -> bool:
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.HOST, self.PORT))
            self.server.listen(4)
        except OSError:
            self.server = None
            return False

        def run() -> None:
            while self.server:
                try:
                    conn, _ = self.server.accept()
                    with conn:
                        payload = json.loads(conn.recv(4096).decode("utf-8"))
                    handler(payload.get("command"))
                except (OSError, ValueError, TypeError):
                    break

        threading.Thread(target=run, name="ipc", daemon=True).start()
        return True

    def close(self) -> None:
        if getattr(self, "server", None):
            self.server.close()
            self.server = None
