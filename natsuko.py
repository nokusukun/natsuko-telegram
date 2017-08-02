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
            if entity.type == 'bot_command':
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


    def api_gen(self, endpoint, **kwargs):

        apiq = self.API_URL + endpoint


        #for arg, value in kwargs.items():
            #if value != None:
               # apiq += f"{arg}={value}&"

            #elif isinstance(value, dict):
             #   value = urllib.parse.quote_plus(value)
              #  apiq += f"{arg}={value}&"

        return apiq, kwargs

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
                    message_id, disable_notification=None):
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

        apiq = self.api_gen("forwardMessage",
                            chat_id=target_cid,
                            from_chat_id=source_cid,
                            message_id=message_id,
                            disable_notification=disable_notification)

        return await self._api_send(apiq)


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

        caption = kwargs.get("caption")
        duration = kwargs.get("duration")
        performer = kwargs.get("performer")
        title = kwargs.get("title")
        disable_notification = kwargs.get("disable_notification")
        reply = kwargs.get("reply")
        reply_markup = kwargs.get("reply_markup")

        if isinstance(audio, str):
            apiq = self.api_gen("sendAudio",
                                chat_id=chat_id,
                                audio=audio,
                                caption=caption,
                                duration=duration,
                                performer=performer,
                                title=title,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            return await self._api_send(apiq)

        else:
            apiq = self.api_gen("sendAudio",
                                chat_id=chat_id,
                                caption=caption,
                                duration=duration,
                                performer=performer,
                                title=title,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            response = await self.session.post(apiq, data=dict(audio=audio))
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

        caption = kwargs.get("caption")
        disable_notification = kwargs.get("disable_notification")
        reply = kwargs.get("reply")
        reply_markup = kwargs.get("reply_markup")

        if isinstance(document, str):
            apiq = self.api_gen("sendDocument",
                                chat_id=chat_id,
                                document=document,
                                caption=caption,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            return await self._api_send(apiq)

        else:
            apiq = self.api_gen("sendDocument",
                                chat_id=chat_id,
                                caption=caption,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            response = await self.session.post(apiq, data=dict(document=document))
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

        caption = kwargs.get("caption")
        duration = kwargs.get("duration")
        width = kwargs.get("width")
        height = kwargs.get("height")
        disable_notification = kwargs.get("disable_notification")
        reply = kwargs.get("reply")
        reply_markup = kwargs.get("reply_markup")

        if isinstance(video, str):
            apiq = self.api_gen("sendVideo",
                                chat_id=chat_id,
                                audio=audio,
                                caption=caption,
                                duration=duration,
                                width=width,
                                height=height,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            return await self._api_send(apiq)

        else:
            apiq = self.api_gen("sendVideo",
                                chat_id=chat_id,
                                caption=caption,
                                duration=duration,
                                width=width,
                                height=height,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            response = await self.session.post(apiq, data=dict(video=video))
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

        caption = kwargs.get("caption")
        duration = kwargs.get("duration")
        disable_notification = kwargs.get("disable_notification")
        reply = kwargs.get("reply")
        reply_markup = kwargs.get("reply_markup")

        if isinstance(voice, str):
            apiq = self.api_gen("sendVoice",
                                chat_id=chat_id,
                                voice=voice,
                                caption=caption,
                                duration=duration,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            return await self._api_send(apiq)

        else:
            apiq = self.api_gen("sendVoice",
                                chat_id=chat_id,
                                caption=caption,
                                duration=duration,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            response = await self.session.post(apiq, data=dict(voice=voice))
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

        duration = kwargs.get("duration")
        disable_notification = kwargs.get("disable_notification")
        reply = kwargs.get("reply")
        reply_markup = kwargs.get("reply_markup")

        if isinstance(v_note, str):
            apiq = self.api_gen("sendVideoNote",
                                chat_id=chat_id,
                                video_note=video_note,
                                duration=duration,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            return await self._api_send(apiq)

        else:
            apiq = self.api_gen("sendVideoNote",
                                chat_id=chat_id,
                                duration=duration,
                                disable_notification=disable_notification,
                                reply_to_message_id=reply,
                                reply_markup=reply_markup)

            response = await self.session.post(apiq, data=dict(video_note=video_note))
            return response.json()


    async def send_location(self, chat_id, long_, lat, **kwargs):
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

        apiq = self.api_gen("sendLocation",
                            chat_id=chat_id,
                            latitude=lat,
                            longitude=long_,
                            disable_notification=kwargs.get("disable_notification"),
                            reply_to_message_id=kwargs.get("reply"),
                            reply_markup=kwargs.get("reply_markup"))

        return await self._api_send(apiq)


    async def send_venue(self, chat_id, long_, title, address, lat, **kwargs):
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

        apiq = self.api_gen("sendVenue",
                            chat_id=chat_id,
                            latitude=lat,
                            longitude=long_,
                            title=title,
                            address=address,
                            disable_notification=kwargs.get("disable_notification"),
                            foursquare_id=kwargs.get("foursquare_id"),
                            reply_to_message_id=kwargs.get("reply"),
                            reply_markup=kwargs.get("reply_markup"))

        return await self._api_send(apiq)


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

        apiq = self.api_gen("sendVenue",
                            chat_id=chat_id,
                            phone_number=phone_number,
                            first_name=first_name,
                            last_name=kwargs.get("last_name"),
                            disable_notification=kwargs.get("disable_notification"),
                            reply_to_message_id=kwargs.get("reply"),
                            reply_markup=kwargs.get("reply_markup"))

        return await self._api_send(apiq)


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

        apiq = self.api_gen("getUserProfilePhotos",
                            user_id=user_id,
                            offset=kwargs.get("offset"),
                            limit=kwargs.get("limit"))

        result = self._api_send(apiq)["result"]
        return DotMap(result)


    async def get_file(self, file_id):

        apiq = self.api_gen("getFile",
                            file_id=file_id)

        result = self._api_send(apiq)
        return DotMap(result)


    async def get_file_url(self, file_obj):

        return "https://api.telegram.org/file/bot{}/{}".format(self.token, file_obj.file_path)


    async def ban_chat_memeber(self, chat_id, user_id, until_date=None):

        apiq = self.api_gen("kickChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            until_date=until_date)

        return await self._api_send(apiq)


    async def unban_chat_memeber(self, chat_id, user_id):

        apiq = self.api_gen("unbanChatMember",
                            chat_id=chat_id,
                            user_id=user_id)

        return await self._api_send(apiq)


    async def restrict_chat_memeber(self, chat_id, user_id, **kwargs):

        apiq = self.api_gen("restrictChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            until_date=kwargs.get("until_date"),
                            can_send_messages=kwargs.get("can_send_messages"),
                            can_send_media_messages=kwargs.get("can_send_media_messages"),
                            can_send_other_messages=kwargs.get("can_send_other_messages"),
                            can_add_web_page_previews=kwargs.get("can_add_web_page_previews"))

        return await self._api_send(apiq)


    async def promote_chat_memeber(self, chat_id, user_id, **kwargs):

        apiq = self.api_gen("promoteChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            can_change_info=kwargs.get("can_change_info"),
                            can_post_messages=kwargs.get("can_post_messages"),
                            can_edit_messages=kwargs.get("can_edit_messages"),
                            can_delete_messages=kwargs.get("can_delete_messages"),
                            can_invite_users=kwargs.get("can_invite_users"),
                            can_restrict_users=kwargs.get("can_restrict_users"),
                            can_pin_messages=kwargs.get("can_pin_messages"),
                            can_promote_members=kwargs.get("can_promote_members"))

        return await self._api_send(apiq)


    async def export_invite_link(self, chat_id):

        apiq = self.api_gen("exportChatInviteLink",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def set_chat_photo(self, chat_id, photo):

        apiq = self.api_gen("setChatPhoto",
                            chat_id=chat_id)

        response = await self.session.post(apiq, data=dict(photo=photo))
        return response.json()


    async def delete_chat_photo(self, chat_id):

        apiq = self.api_gen("deleteChatPhoto",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def set_chat_title(self, chat_id, title):

        apiq = self.api_gen("setChatTitle",
                            chat_id=chat_id,
                            title=title)

        return await self._api_send(apiq)


    async def set_chat_description(self, chat_id, descrption):

        apiq = self.api_gen("setChatDescription",
                            chat_id=chat_id,
                            descrption=descrption)

        return await self._api_send(apiq)


    async def pin_chat_message(self, chat_id, message_id, **kwargs):

        apiq = self.api_gen("pinChatMessage",
                            chat_id=chat_id,
                            message_id=message_id,
                            disable_notification=kwargs.get("disable_notification"))

        return await self._api_send(apiq)


    async def unpin_chat_message(self, chat_id):

        apiq = self.api_gen("unpinChatMessage",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def get_chat(self, chat_id):

        apiq = self.api_gen("getChat",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def get_chat_administrators(self, chat_id):

        apiq = self.api_gen("getChatAdministrators",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def get_chat_member_count(self, chat_id):

        apiq = self.api_gen("getChatMembersCount",
                            chat_id=chat_id)

        return await self._api_send(apiq)


    async def set_chat_member(self, chat_id, user_id):

        apiq = self.api_gen("getChatMember",
                            chat_id=chat_id,
                            user_id=user_id)

        return await self._api_send(apiq)

    # Updating Messages

    async def edit_message_text(self, text, **kwargs):

        apiq = self.api_gen("editMessageText",
                            chat_id=kwargs.get("chat_id"),
                            message_id=kwargs.get("message_id"),
                            inline_message_id=kwargs.get("inline_message_id"),
                            text=text,
                            parse_mode=kwargs.get("parse_mode"),
                            disable_web_page_preview=kwargs.get("disable_web_page_preview"),
                            reply_markup=kwargs.get("reply_markup"))

        return await self._api_send(apiq)


    async def edit_message_caption(self, caption, **kwargs):

        apiq = self.api_gen("editMessageCaption",
                            chat_id=kwargs.get("chat_id"),
                            message_id=kwargs.get("message_id"),
                            inline_message_id=kwargs.get("inline_message_id"),
                            caption=caption,
                            reply_markup=kwargs.get("reply_markup"))

        return await self._api_send(apiq)


    async def edit_message_reply_markup(self, markup, **kwargs):

        apiq = self.api_gen("editMessageReplyMarkup",
                            chat_id=kwargs.get("chat_id"),
                            message_id=kwargs.get("message_id"),
                            inline_message_id=kwargs.get("inline_message_id"),
                            reply_markup=markup)

        return await self._api_send(apiq)


    async def delete_message(self, chat_id, message_id):

        apiq = self.api_gen("deleteMessage",
                            chat_id=chat_id,
                            message_id=message_id)

        return await self._api_send(apiq)
