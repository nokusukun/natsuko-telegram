from natsuko import NatsukoClient
import settings
import yaml

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
def hello_command(event):
    event.reply("Don't hello me you nigger.")


@client.command("image")
def image_command(event):
    client.send_chat_action(event.message.chat.id, 'upload_photo')
    with open('testimage.jpg', 'rb') as f:
        photo = f.read()

    client.send_photo(event.message.chat.id, photo, caption="it's a test photo")

@client.command("info")
def chat_info(event):
    client.send_chat_action(event.message.chat.id, "typing")
    channel = event.message.text[6:]
    x = client.get_chat(channel)
    event.reply(yaml.dump(x))


client.run()
