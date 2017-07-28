
class Message():

    def __init__(self, data, client):
        self.data = data
        self.client = client


    def __getattr__(self, attr):
        if attr == "from":
            return User(self.data.get("from")) if not self.data.get("from") else None
        elif attr == "chat":
            return Chat(self.data.get("chat")) if not self.data.get("chat") else None
        else:
            return self.data.get(attr)


    def reply(self, message):
        self.client.send_message(self.chat.id, message)


class User():

    def __init__(self, data, client):
        self.data = data
        self.client = client


    def __getattr__(self, attr):
        return self.data.get(attr)


class Chat():

    def __init__(self, data, client):
        self.data = data
        self.client = client


    def __getattr__(self, attr):
        return self.data.get(attr)