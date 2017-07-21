from natsuko import NatsukoClient
import settings

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
def hello_command(event):
    event.reply("Don't hello me you nigger.")


@client.command("image")
def image_command(event):
    with open('testimage.jpg', 'rb') as f:
        client.send_image(event.message.chat.id, f, "it's a test photo")

client.run()
