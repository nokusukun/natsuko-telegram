from natsuko import NatsukoClient
import settings

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
def hello_command(event):
    event.reply("Don't hello me you nigger.")


client.run()
