import socket
import RNS
import os
import time

HOST = "localhost"
PORT = 37454
LATEST_LINK = None

class ROB:
    def forward_packet(self, message, packet):
        self.socket.sendall(message)
    def link_established(self, link):
        self.link = link
    def __init__(self):
        reticulum = RNS.Reticulum(None)
        self.socket = None
        # The default configuration path will be expanded to a directory
        # named ".reticulum" inside the current users home directory
        self.configdir    = os.path.expanduser("~")+"/.reticulum"
        self.storagepath  = ""
        self.identity = RNS.Identity()
        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "ROB",
        )
        self.out_destination = None
        self.run = True
        self.send_mode = False
        self.link = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((HOST, PORT))
                s.listen(1)
                conn, addr = s.accept()
                with conn:
                    print('Connected by', addr)
                    self.socket = conn
                    intro = conn.recv(1024)
                    self.handle_intro(intro)
                    conn.sendall(b'OK')
                    while self.run:
                        req = conn.recv(1024)
                        if req.decode() is not '':
                            self.handle_req(req, conn)
                    conn.close()
            except Exception as e:
                print(e)
                s.close()
            
            s.close()

    def handle_intro(self, intro_msg):
        d = intro_msg.decode()
        s = d.split(" ")
        print(s)
        print(len(s))
        identitypath = self.configdir + "/rob/" + s[1]
        print(identitypath)
        if os.path.isfile(identitypath):
            try:
                rob_identity = RNS.Identity.from_file(identitypath)
                if rob_identity != None:
                    RNS.log("Loaded Primary Identity %s from %s" % (str(rob_identity), identitypath))
                else:
                    RNS.log("Could not load the Primary Identity from " + identitypath, RNS.LOG_ERROR)
            except Exception as e:
                RNS.log("Could not load the Primary Identity from " + identitypath, RNS.LOG_ERROR)
                RNS.log("The contained exception was: %s" % (str(e)), RNS.LOG_ERROR)
        else:
            try:
                RNS.log("No Primary Identity file found, creating new...")
                rob_identity = RNS.Identity()
                rob_identity.to_file(identitypath)
                RNS.log("Created new Primary Identity %s" % (str(rob_identity)))
            except Exception as e:
                RNS.log("Could not create and save a new Primary Identity", RNS.LOG_ERROR)
                RNS.log("The contained exception was: %s" % (str(e)), RNS.LOG_ERROR)

        self.identity = rob_identity
        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "ROB",
        )

        print(str(self.destination))

    def handle_req(self, req, conn):
        if self.send_mode:
            p = RNS.Packet(self.link, req, False)
            o = p.send()
            print(o)
            print("Packet sent!")
            self.send_mode = False
            return
        r = req.decode()
        print(r)
        if r.__eq__('QUIT'):
            self.run = False
            return
        
        s = r.split(" ")
        if len(s) > 1 and s[0].__eq__('LINK'):
            destination_hexhash = s[1]

            try:
                if len(destination_hexhash) != 20:
                    raise ValueError("Destination length is invalid, must be 20 hexadecimal characters (10 bytes)")
                destination_hash = bytes.fromhex(destination_hexhash)

            except:
                RNS.log("Invalid destination entered. Check your input!\n")
                exit()

            if not RNS.Transport.has_path(destination_hash):
                RNS.log("Destination is not yet known. Requesting path and waiting for announce to arrive...")
                RNS.Transport.request_path(destination_hash)
                while not RNS.Transport.has_path(destination_hash):
                    time.sleep(0.1)

            out_identity = RNS.Identity.recall(destination_hash)

            RNS.log("Establishing link with destination...")

            self.out_destination = RNS.Destination(
                out_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "ROB",
            )

            t_link = RNS.Link(self.out_destination)

            t_link.set_link_established_callback(self.link_established)

            while not self.link:
                time.sleep(0.1)
            
            print("Link established! " + str(self.link))
            self.link.set_packet_callback(self.forward_packet)
            self.send_mode = True
            conn.sendall(b'OK')

            

if __name__ == "__main__":
    r = ROB()