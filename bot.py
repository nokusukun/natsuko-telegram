from natsuko import NatsukoClient
import settings

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
def hello_command(event):
    client.send_message(event.message.chat.id, "Hello to you as well.")


client.run()
