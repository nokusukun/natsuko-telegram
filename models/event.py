from dotmap import DotMap

class Message():

    def __init__(self, client, data):

        self.data = data
        self.client = client
        self.original = data

        self._populate()

    def __getattr__(self, attr):
        # if message attribute is missing (not included in data)
        # return None
        return None

    def _populate(self):

        for attr, value in self.original.items():
            if attr == 'from':
                setattr(self, 'user', User(value))

            elif attr == 'chat':
                setattr(self, attr, Chat(value))

            else:
                setattr(self, attr, value)


class Entity():

    def __init__(self, entity):
        self.type = entity['type']
        self.offset = entity['offset']
        self.length = entity['length']

        self.bot_command = self.type == 'bot_command'


class Chat():

    def __init__(self, chat):
        self.all_members_are_administrators = chat['all_members_are_administrators']
        self.id = chat['id']
        self.title = chat['title']
        self.type = chat['type']

    def __str__(self):
        return f"(Chat) | id: {self.id}, title: {self.title}, type: {self.type}"

class User():

    def __init__(self, user):
        self.first_name = user['first_name']
        self.id = user['id']
        self.username = user['username']

    def __str__(self):
        return f"(User) | id: {self.id}, username: {self.username}"


class Event():

    def __init__(self, client, event):
        self.message = Message(client, event.message)

        self.update_id = event.update_id
        self.chat = self.message.chat
        self.raw_event = event
        self.client = client

        self.entities = DotMap()
        self.entities.mention = self.get_entities("mention")
        self.entities.bot_command = self.get_entities("bot_command")
        self.entities.hashtag = self.get_entities("hashtag")
        self.entities.url = self.get_entities("url")
        self.entities.email = self.get_entities("email")
        self.entities.bold = self.get_entities("bold")
        self.entities.italic = self.get_entities("italic")
        self.entities.code = self.get_entities("code")
        self.entities.pre = self.get_entities("pre")
        self.entities.text_link = self.get_entities("text_link")
        self.entities.text_mention = self.get_entities("text_mention")


    def get_entities(self, t):
        return [self.message.text[x.offset: x.offset+x.length] for x in self.message.entities if x["type"] == t]


    async def reply(self, message):
        return await self.client.send_message(self.chat.id, message)


    async def reply_photo(self, photo):
        return await self.client.send_photo(self.chat.id, photo)


    async def forward(self, chat_id):
        return await self.client.forward_message(chat_id, self.chat.id, self.message.message_id)
