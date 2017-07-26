from natsuko import NatsukoClient
import settings
import yaml

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
async def hello_command(event):
    # event.reply("Don't hello me you nigger.")
    await event.reply("dont hello me you nigglet.")

@client.command("image")
async def image_command(event):
    await client.send_chat_action(event.message.chat.id, 'upload_photo')
    with open('testimage.jpg', 'rb') as f:
        photo = f.read()

    await client.send_photo(event.message.chat.id, photo, caption="it's a test photo")

@client.command("info")
async def chat_info(event):
    await client.send_chat_action(event.message.chat.id, "typing")
    channel = event.message.text[6:]
    x = await client.get_chat(channel)
    await client.send_message(event.message.chat.id, yaml.dump(x))


client.run()
