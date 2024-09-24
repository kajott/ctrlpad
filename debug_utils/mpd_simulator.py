#!/usr/bin/env python3
"""
Dummy server that speaks the MPD control protocol. For debugging purposes only.
"""
import logging
import random
import socketserver
import time

class MPDState:
    def __init__(self):
        self.state = "stop"
        self.song = 0
        self.songid = 0
        self._start = None
        self.elapsed = 0
        self.duration = 0
        self.playlistlength = 0
        self.volume = 100

    def addtracks(self):
        self.playlistlength += random.randrange(10, 100)

    def play(self):
        if self.state == "play":
            return
        elif self.state == "stop":
            self.newtrack()
        else:  # paused
            self._start = time.time() - self.elapsed
        self.state = "play"

    def update(self):
        if self.state != "play":
            return
        self.elapsed = time.time() - self._start
        if self.elapsed > self.duration:
            self.newtrack()

    def newtrack(self):
        self.song = random.randrange(self.playlistlength or 1)
        self.songid = random.randrange(1000000, 10000000)
        self.duration = random.random() * 300 + 60
        self._start = time.time()
        self.elapsed = 0

g_state = MPDState()

class MPDServerConnection(socketserver.StreamRequestHandler):
    def handle(self):
        global g_state
        self.log = logging.getLogger(":".join(map(str, self.client_address)))
        self.log.info("vvvvv connected vvvvv")
        self.send("OK MPD 0.8.15")
        try:
            while True:
                cmd = self.rfile.readline().strip().decode('utf-8', 'replace')
                if not cmd: break
                self.log.info("RECV '%s'", cmd)
                if cmd == "status":
                    if not random.randrange(10):
                        delay = random.randrange(10, 151)
                        self.log.info("<<<<< delaying by %d ms >>>>>", delay)
                        time.sleep(delay / 1000)
                    g_state.update()
                    for field in ("state", "song", "playlistlength", "songid", "elapsed", "duration", "volume"):
                        self.send(f"{field}: {getattr(g_state, field)}")
                elif cmd == "currentsong":
                    self.send(f"file: id{g_state.songid}.mp3")
                elif cmd == "play":
                    g_state.play()
                elif cmd == "stop":
                    g_state.state = "stop"
                elif cmd == "pause 1":
                    g_state.state = "pause"
                elif cmd in ("previous", "next"):
                    g_state.newtrack()
                elif cmd.startswith("add "):
                    g_state.addtracks()
                self.send("OK")
        except EnvironmentError as e:
            self.log.error("%s", str(e))
        self.log.info("^^^^^ disconnected ^^^^^")

    def send(self, line):
        self.log.info("SEND '%s'", line)
        self.wfile.write(line.encode('utf-8') + b'\n')

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    try:
        with socketserver.ThreadingTCPServer(('localhost', 6600), MPDServerConnection) as server:
            logging.info("listening on %s:%d", *server.server_address)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    logging.info("server stopped")
