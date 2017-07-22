from dotmap import DotMap

class Event():

	def __init__(self, client, event):
		self.message = event.message
		self.update_id = event.update_id
		self.chat = event.message.chat
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


	def reply(self, message):
		return self.client.send_message(self.chat.id, message)


	def reply_photo(self, photo):
		return self.client.send_photo(self.chat.id, photo)


	def forward(self, chat_id):
		return self.client.forward_message(chat_id, self.chat.id, self.message.message_id)