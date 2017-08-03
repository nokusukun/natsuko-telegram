import threading
import requests
import json
import time
import urllib.parse
from dotmap import DotMap

from models.types import Event, Message
from models.errors import APIError
import asyncio
import aiohttp
import traceback
from pprint import pprint


class UpdateManager():

    def __init__(self, **kwargs):
        self.loop = asyncio.get_event_loop()

        self.session = kwargs.get("session")
        self.token = kwargs.get("token")
        self.callback = kwargs.get("callback")

        self.poll_timeout = 100

        self.URL = f"https://api.telegram.org/bot{self.token}/"

        self.last_update = None
        self.command_queue = []


    async def update_loop(self):
        print("Starting Poll Update Loop")

        while True:
            await self.poll_updates(self.last_update)


    async def poll_updates(self, offset=None):

        url = f"{self.URL}getUpdates?timeout={self.poll_timeout}"

        if offset:
            url += f"&offset={offset}"

        async with self.session.get(url) as resp:
            data = await resp.json()
            result = data['result']

            if result:
                self.command_queue.extend(result)
                self.last_update = max(x["update_id"] for x in result) + 1
                print(f"Poll Successful: {self.last_update}")
                await self.callback()



class NatsukoClient():

    def __init__(self, token, **kwargs):
        self.token = token
        self.API_URL = f"https://api.telegram.org/bot{self.token}/"

        self.commands = {}
        self.usercache = {}

        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.manager = UpdateManager(token=self.token, session=self.session, callback=self.process)


    def run(self):

        self.loop.run_until_complete(self._run())

    async def _run(self):

        task = asyncio.ensure_future(self.manager.update_loop())
        await task


    async def process(self):
        print(f"Callback Called: {self}")

        while self.manager.command_queue:
            _cmd = DotMap(self.manager.command_queue.pop(0))
            command = Event(self, _cmd)
            self.parse_command(command)


    def parse_command(self, event):

        for entity in event.message.entities:
            if entity.is_command:
                command = entity.text[1:]
                print(f"Identified as Bot Command: {entity}")

                if command in self.commands:
                    func = self.commands[command]["function"]
                    asyncio.ensure_future(func(event))

        user = event.message.author
        if not user.username in self.usercache:
            self.usercache[user.username] = user

        #
        # not sure that any of this shit is necessary
        #
        # if "message" in event and not raw_command.message.keys():
            # if not username in self.usercache:
                # self.usercache[username] = raw_command.message["from"]

        # elif "inline_query" in raw_command:
            # if not username in self.usercache:
                # self.usercache[username] = raw_command.inline_query["from"]

        # elif "chat" in raw_command:
            # if not username in self.usercache:
                # self.usercache[username] = raw_command.chat["from"]



    # Command Decorator
    def command(self, name, **options):

        def deco(f):
            command = {"function": f}
            command["no_error"] = False if "no_error" not in options else options["no_error"]

            self.commands[name] = command
            print(f'\tLOAD_OK: {f.__name__}: on_command @ {name}')

            return f

        return deco


    async def _api_send(self, url, apiq):
        print(f"APISEND: {apiq}")

        async with self.session.get(url, params=apiq) as resp:
            content = await resp.json()

            if not content["ok"]:
                raise APIError(content)

            return content["result"]


    async def send_message(self, chat_id, message, **kwargs):
        """
            Use this method to send text messages. On success, the sent Message is returned.
            (Optional parameters are keyword arguments)

            Parameters                  Type    Required    Description
            chat_id                     Int/Str Yes         Unique identifier for the target chat or username of
                                                            the target channel (in the format @channelusername)
            text                        String  Yes         Text of the message to be sent
            parse_mode*                 String  Optional    Send Markdown or HTML, if you want Telegram apps to
                                                            show bold, italic, fixed-width text or inline URLs
                                                            in your bot's message.
            disable_web_page_preview*   Boolean Optional    Disables link previews for links in this message
            disable_notification*       Boolean Optional    Sends the message silently. Users will receive a
                                                            notification with no sound.
            reply*                      Integer Optional    If the message is a reply, ID of the original message
            reply_markup*               Json    Optional    Additional interface options. A JSON-serialized
                                                            object for an inline keyboard, custom reply keyboard,
                                                            instructions to remove reply keyboard or to force a
                                                            reply from the user.
        """

        endpoint = "sendMessage"

        url = self.API_URL + endpoint
        args = {"chat_id": chat_id, "text": message, **kwargs}
        return await self._api_send(url, args)


    async def forward_message(self, target_cid, source_cid,
                    message_id, **kwargs):
        """
        Use this method to forward messages of any kind. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type    Required    Description
        chat_id                 Int/Str Yes         Unique identifier for the target chat or username of the
                                                    target channel (in the format @channelusername)
        from_chat_id            Int/Str Yes         Unique identifier for the chat where the original message
                                                    was sent (or channel username in the format
                                                    @channelusername)
        disable_notification    Boolean Optional    Sends the message silently. Users will receive a
                                                    notification with no sound.
        message_id              Integer Yes         Message identifier in the chat specified in from_chat_id
        """

        endpoint = "forwardMessage"

        url = self.API_URL + endpoint
        args = {'chat_id': target_cid, 'from_chat_id': source_cid, 'message_id': message_id, **kwargs}

        return await self._api_send(url, args)


    async def send_photo(self, chat_id, photo, **kwargs):
        """Use this method to send photos. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        photo                   File/Str    Yes         Photo to send. Pass a file_id or a binary filestream.
        caption                 String      Optional    Photo caption (may also be used when resending photos
                                                        by file_id), 0-200 characters
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = 'sendPhoto'
        url = self.API_URL + endpoint

        if isinstance(photo, str):
            if photo.startswith('http'):
                photo = urllib.parse.quote(photo)

            args = {"chat_id": chat_id, "photo": photo, **kwargs}
            return await self._api_send(url, args)

        else:
            args = {"chat_id": chat_id, **kwargs}
            response = await self.session.post(url, data=dict(photo=photo), params=args)
            return response.json()


    async def send_audio(self, chat_id, audio, **kwargs):
        """Use this method to send audio, if you want Telegram clients to display them in the music
        player. Your audio must be in the .mp3 format. On success, the sent Message is returned.
        Bots can currently send audio files of up to 50 MB in size, this limit may be changed in the
        future. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        audio                   File/Str    Yes         Audio file to send. Pass a file_id or a
                                                        binary filestream.
        caption                 String      Optional    Audio Caption, 0-200 characters
        duration                Integer     Optional    Duration of the audio in seconds
        performer               String      Optional    Performer
        title                   String      Optional    Track name
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendAudio"

        url = self.API_URL + endpoint

        if isinstance(audio, str):
            args = {'chat_id': chat_id, 'audio': audio, **kwargs}
            return await self._api_send(url, args)

        else:
            args = {'chat_id': chat_id, **kwargs}
            response = await self.session.post(url, data=dict(audio=audio), params=args)
            return response.json()


    async def send_document(self, chat_id, document, **kwargs):
        """Use this method to send documents.  Bots can currently send files of any type of up to 50 MB
        in size, this limit may be changed in the future. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        document                File/Str    Yes         File to send. Pass a file_id or a
                                                        binary filestream.
        caption                 String      Optional    Caption, 0-200 characters
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendDocument"

        if isinstance(document, str):
            args = {'chat_id': chat_id, 'document': document, **kwargs}
            return await self._api_send(url, args)

        else:
            args = {'chat_id': chat_id, **kwargs}
            response = await self.session.post(url, data=dict(document=document), params=args)
            return response.json()


    async def send_video(self, chat_id, video, **kwargs):
        """Use this method to send videos. Telegram clients support mp4 videos
        (other formats may be sent as Document). On success, the sent Message is returned.
        Bots can currently send video files of up to 50 MB in size, this limit may be changed
        in the future.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        video                   File/Str    Yes         File to send. Pass a file_id or a
                                                        binary filestream.
        caption                 String      Optional    Caption, 0-200 characters
        duration                Integer     Optional    Duration of sent video in seconds
        width                   Integer     Optional    Video width
        height                  Integer     Optional    Video height
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendVideo"

        url = self.API_URL + endpoint

        if isinstance(video, str):
            args = {"chat_id": chat_id, "video": video, **kwargs}
            return await self._api_send(url, args)

        else:
            args = {"chat_id": chat_id, **kwargs}
            response = await self.session.post(url, data=dict(video=video), params=args)
            return response.json()


    async def send_voice(self, chat_id, voice, **kwargs):
        """Use this method to send voice files. if you want Telegram clients to display the file as a
        playable voice message. For this to work, your audio must be in an .ogg file encoded with OPUS
        (other formats may be sent as Audio or Document). On success, the sent Message is returned.
        Bots can currently send voice messages of up to 50 MB in size, this limit may be changed in
        the future.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        voice                   File/Str    Yes         File to send. Pass a file_id or a
                                                        binary filestream.
        caption                 String      Optional    Caption, 0-200 characters
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendVoice"

        url = self.API_URL + endpoint

        if isinstance(voice, str):
            args = {"chat_id": chat_id, "voice": voice, **kwargs}
            return await self._api_send(apiq)

        else:
            args = {"chat_id": chat_id, **kwargs}
            response = await self.session.post(url, data=dict(voice=voice), params=args)
            return response.json()


    async def send_video_note(self, chat_id, v_note, **kwargs):
        """As of v.4.0, Telegram clients support rounded square mp4 videos of up to 1 minute long.
        Use this method to send video messages. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        video                   File/Str    Yes         File to send. Pass a file_id or a
                                                        binary filestream.
        caption                 String      Optional    Caption, 0-200 characters
        duration                Integer     Optional    Duration of sent video in seconds
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendVideoNote"
        url = self.API_URL + endpoint

        if isinstance(v_note, str):
            args = {"chat_id": chat_id, "video_note": v_note}
            return await self._api_send(url, args)

        else:
            args = {"chat_id": chat_id}
            response = await self.session.post(url, data=dict(video_note=v_note), params=args)
            return response.json()


    async def send_location(self, chat_id, long, lat, **kwargs):
        """Use this method to send point on the map. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        latitude                Float       Yes         Latitude of location
        longitude               Float       Yes         Longitude of location
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = 'sendLocation'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, "latitude": lat, "longitutde": long, **kwargs}
        return await self._api_send(url, args)


    async def send_venue(self, chat_id, lat, long, title, addr, **kwargs):
        """Use this method to send information about a venue. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        latitude                Float       Yes         Latitude of location
        longitude               Float       Yes         Longitude of location
        title                   String      Yes         Name of the venue
        address                 String      Yes         Address of the venue
        foursquare_id           String      Optional    Foursquare identifier of the venue
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = "sendVenue"
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'latitude': lat, "longitude": long, 'title': title, 'address': addr}
        return await self._api_send(url, args)


    async def send_contact(self, chat_id, phone_number, first_name, **kwargs):
        """Use this method to send information about a venue. On success, the sent Message is returned.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        phone_number            String      Yes         Contact's phone number
        first_name              String      Yes         Contact's first name
        last_name               String      Optional    Contact's last name
        disable_notification    Boolean     Optional    Sends the message silently. Users will receive a
                                                        notification with no sound.
        reply                   Integer     Optional    If the message is a reply, ID of the original message
        reply_markup            Json        Optional    Additional interface options. A JSON-serialized object
                                                        for an inline keyboard, custom reply keyboard,
                                                        instructions to remove reply keyboard or to
                                                        force a reply from the user.
        """

        endpoint = 'sendContact'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'phone_number': phone_number, 'first_name': first_name, **kwargs}
        return await self._api_send(url, args)


    async def send_chat_action(self, chat_id, action):
        """Use this method when you need to tell the user that something is happening on the bot's side.
        The status is set for 5 seconds or less (when a message arrives from your bot,
        Telegram clients clear its typing status). Returns True on success.

        Example: The ImageBot needs some time to process a request and upload the image.
        Instead of sending a text message along the lines of “Retrieving image, please wait…”,
        the bot may use sendChatAction with action = upload_photo. The user will see a “sending photo”
        status for the bot.

        We only recommend using this method when a response from the bot will take a noticeable
        amount of time to arrive.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        chat_id                 Int/Str     Yes         Unique identifier for the target chat or username of
                                                        the target channel (in the format @channelusername)
        action                  String      Yes         Type of action to broadcast. Choose one, depending on
                                                        what the user is about to receive:
                                                        'typing' for text messages,
                                                        'upload_photo' for photos,
                                                        'record_video' or 'upload_video' for videos,
                                                        'record_audio' or 'upload_audio' for audio files,
                                                        'upload_document' for general files,
                                                        'find_location' for 'location data',
                                                        'record_video_note' or 'upload_video_note'
                                                            for video notes.
        """

        endpoint = "sendChatAction"
        url = self.API_URL + endpoint

        args = {'chat_id': str(chat_id), 'action': action}
        return await self._api_send(url, args)


    async def get_user_profile_photos(self, user_id, **kwargs):
        """Use this method to get a list of profile pictures for a user.
        Returns a UserProfilePhotos Dictionary.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        user_id                 Int/Str     Yes         Unique identifier for the target user.
        offset                  Integer     Optional    Sequential number of the first photo to be returned.
                                                        By default, all photos are returned.
        limit                   Integer     Optional    Limits the number of photos to be retrieved.
                                                        Values between 1—100 are accepted. Defaults to 100
        """

        endpoint = 'getUserProfilePhotos'
        url = self.API_URL + endpoint

        args = {'user_id': user_id, **kwargs}
        return await self._api_send(url, args)


    async def get_file(self, file_id):

        endpoint = 'getFile'
        url = self.API_URL + endpoint

        args = {'file_id': file_id}
        return await self._api_send(url, args)

    async def get_file_url(self, file_obj):

        return f"https://api.telegram.org/file/bot{self.token}/{file_obj.file_path}"


    async def ban_chat_memeber(self, chat_id, user_id, **kwargs):

        endpoint = "kickChatMember"
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'user_id': user_id, **kwargs}
        return await self._api_send(url, args)


    async def unban_chat_memeber(self, chat_id, user_id):

        endpoint = 'unbanChatMember'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'user_id': user_id}
        return await self._api_send(url, args)


    async def restrict_chat_memeber(self, chat_id, user_id, **kwargs):

        endpoint = 'restrictChatMember'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'user_id': user_id, **kwargs}
        return await self._api_send(url, args)


    async def promote_chat_memeber(self, chat_id, user_id, **kwargs):

        endpoint = 'promoteChatMember'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'user_id': user_id, **kwargs}
        return await self._api_send(url, args)


    async def export_invite_link(self, chat_id):

        endpoint = 'exportChatInviteLink'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def set_chat_photo(self, chat_id, photo):

        endpoint = 'sendChatPhoto'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        response = await self.session.post(apiq, data=dict(photo=photo), params=args)
        return response.json()


    async def delete_chat_photo(self, chat_id):

        endpoint = 'deleteChatPhoto'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def set_chat_title(self, chat_id, title):

        endpoint = 'setChatTitle'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'title': title}
        return await self._api_send(url, args)


    async def set_chat_description(self, chat_id, desc):

        endpoint = 'setChatDescription'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'description': desc}
        return await self._api_send(url, args)


    async def pin_chat_message(self, chat_id, message_id, **kwargs):

        endpoint = 'pinChatMessage'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'message_id': message_id, **kwargs}
        return await self._api_send(url, args)


    async def unpin_chat_message(self, chat_id):

        endpoint = 'unpinChatMessage'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def get_chat(self, chat_id):

        endpoint = 'getChat'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def get_chat_administrators(self, chat_id):

        endpoint = 'getChatAdministrators'

        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def get_chat_member_count(self, chat_id):

        endpoint = 'getChatMembersCount'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    async def get_chat_member(self, chat_id, user_id):

        endpoint = 'getChatMember'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id}
        return await self._api_send(url, args)


    # Updating Messages

    async def edit_message_text(self, chat_id, msg_id, text, **kwargs):

        endpoint = 'editMessageText'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'text': text, 'message_id': msg_id, **kwargs}
        return await self._api_send(url, args)


    async def edit_message_caption(self, chat_id, msg_id, caption, **kwargs):

        endpoint = 'editMessageCaption'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'message_id': msg_id, 'caption': caption, **kwargs}
        return await self._api_send(url, args)


    async def edit_message_reply_markup(self, chat_id, msg_id, markup, **kwargs):

        endpoint = 'editMessageReplyMarkup'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'message_id': msg_id, 'markup': markup, **kwargs}
        return await self._api_send(url, args)


    async def delete_message(self, chat_id, msg_id):

        endpoint = 'deleteMessage'
        url = self.API_URL + endpoint

        args = {'chat_id': chat_id, 'message_id': msg_id}
        return await self._api_send(url, args)
