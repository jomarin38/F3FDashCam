from threading import Thread

from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2
from datetime import datetime
import os
import shutil
from pathlib import Path
import time
import socket
import json

MEDIA_DIR = '/home/pi/Videos'
MEDIA_QUOTA = 10* (2**30)
GARBAGE_COLLECTION_RATIO = 0.25

class GarbageCollector(Thread):
    def __init__(self, target_space):
        Thread.__init__(self)
        self.stopped = False
        self.target_space = target_space

    def run(self):
        paths = sorted(Path(MEDIA_DIR).iterdir(), key=os.path.getmtime)
        saved_space = 0
        i = 0
        while i <= len(paths) and saved_space<self.target_space:
            file_to_remove = str(paths[i])
            saved_space += os.stat(file_to_remove).st_size
            i += 1
            print('Removing {}'.format(file_to_remove))
            os.remove(file_to_remove)


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

class tcpClient_Status():
    Init = 0
    Listen = 1
    Accepted = 2
    Connected = 3
    InProgress = 4
    Close = 5

class DashcamTCPClient(Thread):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def __init__(self, server_ip, server_port):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration())
        self.encoder = H264Encoder()
        self.running = False
        self.stop = False
        self.server_ip = server_ip
        self.server_port = server_port
        self.__debug = True
        self.timer_thread = None
        self.status = tcpClient_Status.Init
        super().__init__()

    def run(self):
        self.start_anonymous_recording()
        while not self.stop:
            if self.status == tcpClient_Status.Init:
                try:
                    gateway = self.server_ip
                    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client.connect((gateway, self.server_port))
                except socket.error as e:
                    print(str(e))
                    del (self.client)
                    self.client = None
                    time.sleep(5)
                else:
                    if self.__debug:
                        print(f'Connection...')
                    self.status = tcpClient_Status.Connected
            elif self.status == tcpClient_Status.Connected:
                data = ''
                try:
                    self.client.sendall(bytes("F3Fdashcam", "utf-8"))
                except socket.error as e:
                    print(str(e))
                try:
                    data = str(self.client.recv(1024), "utf-8")
                except socket.error as e:
                    print(str(e))
                if self.__debug:
                    print(f'data received : {data}')
                if data == "dashcamServerStarted":
                    self.status = tcpClient_Status.InProgress
            elif self.status == tcpClient_Status.InProgress:
                try:
                    data = self.client.recv(2048)
                except socket.error as e:
                    print(str(e))
                else:
                    if data == b'':
                        try:
                            self.client.sendall(bytes("Test", "utf-8"))
                        except socket.error as e:
                            print(str(e))
                            self.client.close()
                            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.status = tcpClient_Status.Init
                            del self.client
                            self.client = None
                    else:
                        self.datareceived(data)
            elif self.status == tcpClient_Status.Close:
                self.client.close()
                self.status = tcpClient_Status.Close

    def datareceived(self, data):
        print(data)
        m = data.decode('utf-8').split()
        if len(m)>0:
            if m[0] == "ContestData":
                orderstring = data.decode('utf-8')[len(m[0]) + 1:]
                if self.__debug:
                    print('datasize:' + str(len(orderstring)))
                    print(orderstring)
                orderjson = json.loads(orderstring)
                self.start_recording_with_context(orderjson['pilot'], orderjson['round'])

    def sequence_timeout(self):
        self._stop_recording()
        self.start_anonymous_recording()

    def _stop_recording(self):
        if self.running:
            self.picam2.stop_recording()
            self.running = False

    def start_anonymous_recording(self):
        filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.h264'
        self._start_recording(os.path.join(MEDIA_DIR, filename))


    def start_recording_with_context(self, pilot_name, round_number):
        filename = '{}_{}_{}.h264'.format(str(round_number),
                                          '_'.join(pilot_name.split()),
                                          datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
        self._start_recording(os.path.join(MEDIA_DIR, filename))


    def _start_recording(self, filename):
        used = self._get_dir_size(MEDIA_DIR)
        if used > MEDIA_QUOTA:
            print('Usage : {}, Quota : {}'.format(used, MEDIA_QUOTA))
            garbage_collector_thread = GarbageCollector(int(MEDIA_QUOTA*GARBAGE_COLLECTION_RATIO))
            garbage_collector_thread.start()
        if self.timer_thread is not None:
            self.timer_thread.ignore_event()
        self._stop_recording()
        self.running = True
        self.picam2.start_recording(self.encoder, filename, quality=Quality.MEDIUM)
        self.timer_thread = TimerThread(self)
        self.timer_thread.start()

    def _get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size(entry.path)
        return total

if __name__ == "__main__":
    HOST, PORT = "192.168.0.13", 10000

    tcp_thread = DashcamTCPClient(HOST, PORT)
    tcp_thread.start()
    tcp_thread.join()
