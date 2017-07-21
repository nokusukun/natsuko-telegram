import threading
import requests
import json
import time
import urllib.parse
from dotmap import DotMap

from models.event import Event


class UpdateManager():
    

    def __init__(self, **kwa):
        self.callback = kwa["callback"]
        self.token = kwa["token"]
        self.poll_timeout = kwa["poll_timeout"]
        self.URL = "https://api.telegram.org/bot{}/".format(self.token)

        self.last_update = None
        self.command_queue = []

        self.queue_empty = True

        loop = threading.Thread(target=self.update_loop)
        loop.daemon = True
        loop.start()
        print("Done")


    def get_command(self):
        command = self.command_queue.pop(0)
        if not self.command_queue:
            self.queue_empty = True

        return DotMap(command)


    def update_loop(self):
        print("Starting Poll Update Loop")
        while True:
            self.poll_updates(self.last_update)
            

    def poll_updates(self, offset=None):
        try:
            url = self.URL + "getUpdates?timeout={}".format(self.poll_timeout)
            if offset:
                url += "&offset={}".format(offset)

            response = requests.get(url).content.decode("utf8")
            js = json.loads(response)["result"]
            self.command_queue.extend(js)
            self.last_update = max(x["update_id"] for x in js) + 1
            print("Poll Successful: {}".format(self.last_update))
            self.queue_empty = False
        except:
            pass



class NatsukoClient():


    def __init__(self, token):
        self.token = token
        self.poll_timeout = 100
        self.commands = {}

        self.APIL = "https://api.telegram.org/bot{}/".format(self.token)

        self.manager = None
        self.com_proc_running = False

    def run(self):
        self.manager = UpdateManager(token=self.token, callback=self.process, poll_timeout=100)
        self.process()


    def process(self):
        while True:

            while not self.manager.queue_empty:
                raw_command = self.manager.get_command()

                if "bot_command" in [x["type"] for x in raw_command.message.entities]:
                    print("Identified as Bot Command")

                    # Gets the bot_command entity
                    e = [x for x in raw_command.message.entities if x["type"] == "bot_command"][0]
                    command = raw_command.message.text[e.offset + 1: e.offset + e.length]
                    if command in self.commands:
                        self.commands[command]["function"](Event(self, raw_command))

            while self.manager.queue_empty:
                time.sleep(0.5)


    # Command Decorator
    def command(self, name, **options):

        def deco(f):
            command = {"function": f}
            command["no_error"] = False if "no_error" not in options else options["no_error"]

            self.commands[name] = command
            print('\tLOAD_OK: {0.__name__}: on_command @ {1}'.format(f, name))

            return f
        return deco


    def api_gen(self, endpoint, **kwa):
        apiq = "{}{}?".format(self.APIL, endpoint)
        for arg, val in kwa.items():
            apiq += "{}={}&".format(arg, val)
        return apiq[:-1]


    def _api_send(self, apiq):
        response = requests.get(apiq)
        content = response.content.decode("utf8")
        return content


    def send_message(self, chat_id, message):
        message = urllib.parse.quote_plus(message)
        apiq = self.api_gen("sendMessage", text=message, chat_id=chat_id)
        self._api_send(apiq)
