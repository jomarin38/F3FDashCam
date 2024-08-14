from threading import Thread

from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2
from datetime import datetime
import time

class TimerThread(Thread):
    def __init__(self, camera_handler):
        Thread.__init__(self)
        self.stopped = False
        self.camera_handler = camera_handler

    def ignore_event(self):
        self.stopped = True

    def run(self):
        time.sleep(5 * 60)
        if not self.stopped:
            self.camera_handler.sequence_timeout()

import socketserver

class DashcamTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def __init__(self, camera):
        self.picam2 = Picamera2()
        self.picam2.configure(picam2.create_video_configuration())
        self.encoder = H264Encoder()
        self.running = False

    def sequence_timeout(self):
        self._stop_recording()
        self.start_anonymous_recording()

    def _stop_recording(self):
        if self.running:
            self.picam2.stop_recording()
            self.running = False

    def start_anonymous_recording(self):
        filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.h264'
        self._start_recording(filename)


    def start_recording_with_context(self, pilot_name, round_number):
        filename = '{}_{}_{}.h264'.format(pilot_name,
                                          str(round_number),
                                          datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
        self._start_recording(filename)


    def _start_recording(self, filename):
        self._stop_recording()
        self.running = True
        picam2.start_recording(encoder, filename, quality=Quality.HIGH)
        timer_thread = TimerThread(self)
        timer_thread.start()

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        print("{} wrote:".format(self.client_address[0]))
        print(self.data)
        # just send back the same data, but upper-cased
        self.request.sendall(self.data.upper())
        # here you can do self.request.sendall(use the os library and display the ls command)

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999



    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((HOST, PORT), DashcamTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()