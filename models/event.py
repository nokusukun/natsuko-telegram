

class Event():

	def __init__(self, client, event):
		self.message = event.message
		self.update_id = event.update_id
		self.chat = event.message.chat
		self.raw_event = event
		self.client = client


	def reply(self, message):
		self.client.send_message(self.chat.id, message)