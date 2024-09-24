#!/usr/bin/env python3
"""
Minimal simulation of the SIS protocol as implemented by Extron DXP switches.
Really only supports enough of the protocol to talk to ctrlpad's Crossbar class.
"""
import sys
import socketserver

class ConnectionHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"(c) Copyright 20nn, Extron Electronics DXP DVI-HDMI, Vn.nn, 60-nnnn-01\r\nDdd, DD Mmm YYYY HH:MM:SS\r\n")
        try:
            print("connected")
            buf = b""
            cmd = None
            wait = False
            while True:
                if cmd:
                    if pos > 0:
                        print("dummy data:", repr(buf[:pos]))
                    print(cmd + " command:", repr(buf[pos:]))
                    if response:
                        self.request.sendall(response.encode())
                    buf = b""
                    wait = False
                cmd = response = None
                pos = 0
            
                c = self.request.recv(1)
                if not c:
                    print("disconnected")
                    return
                buf += c
                # print("\x1b[2m" + repr(buf) + "\x1b[0m")

                # detect multi-tie command
                if buf.endswith(b"\x1b+Q"):
                    # print("multi-tie detected, waiting for end")
                    wait = True
                    continue

                # detect single-tie command
                if not(wait) and (buf[-1:] in b"!&%$"):
                    pos = buf.rfind(b"*")
                    if pos < 1:
                        print("bogus command:", repr(buf))
                        buf = b""
                        continue
                    while pos and buf[pos-1:pos].isdigit(): pos -= 1
                    cmd = "single tie"
                    response = "OutX InY All\r\n"
                    continue

                # detect status command
                if not(wait) and (buf == b"I"):
                    cmd = "info"
                    response = "V8X8 A8X8\r\n"
                    continue

                # detect status command
                if not(wait) and (buf in b"XNQS"):
                    cmd = "status"
                    response = "whatever\r\n"
                    continue

                # check for end-of-line
                if buf[-1:] != b"\n":
                    continue
                
                # handle multi-tie command
                pos = buf.find(b"\x1b+Q")
                if pos >= 0:
                    cmd = "multi tie"
                    response = "Qik\r\n"
                    continue

                # handle EDID upload command
                edid = buf.find(b"EDID")
                pos = buf.find(b"\x1bI")
                if (pos >= 0) and (edid > pos):
                    cmd = "EDID upload"
                    response = "EdidI" + buf[pos+2 : edid] + "\r\n"
                    bytes_left = 256
                    while bytes_left > 0:
                        bytes_left -= len(self.request.recv(bytes_left))
                    continue

                # handle EDID assign command
                edid = buf.find(b"*EDID")
                pos = buf.find(b"\x1bA")
                if (pos >= 0) and (edid > pos):
                    cmd = "EDID assign"
                    response = "EdidA0*" + buf[pos+2 : edid] + "\r\n"
                    continue

                # handle ordinary end-of-line
                if buf.strip():
                    print("unrecognized command:", repr(buf))
                else:
                    print("whitespace:", repr(buf))
                buf = b""

        except EnvironmentError as e:
            print("connect error:", e)

class TCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    if sys.platform == "win32":
        import os
        os.system("")  # makes ANSI codes available
    TCPServer(("localhost", 2323), ConnectionHandler).serve_forever()
