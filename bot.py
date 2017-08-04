from natsuko import NatsukoClient
import settings
import yaml

client = NatsukoClient(settings.TOKEN)

@client.command("hello")
async def hello_command(event):
    await event.chat.send_message("dont hello me you nigglet.")

    stickers = await client.get_sticker_set("machiko")
    sticker = stickers.stickers[0]

    await event.chat.send_sticker(sticker)

@client.command("image")
async def image_command(event):
    with open('testimage.jpg', 'rb') as f:
        photo = f.read()

    await event.chat.send_photo(photo, caption="it's a test photo")

@client.command("info")
async def chat_info(event):
    await client.send_chat_action(event.message.chat.id, "typing")
    channel = event.message.text[6:]
    x = await client.get_chat(channel)

    await client.send_message(event.message.chat.id, yaml.dump(x))


client.run()
