import threading
import requests
import json
import time
import urllib.parse
from dotmap import DotMap

from models.event import Event
from models.errors import APIError


class UpdateManager():
    

    def __init__(self, **kwa):
        self.callback = kwa.get("callback")
        self.token = kwa.get("token")
        self.poll_timeout = kwa.get("poll_timeout")
        self.URL = "https://api.telegram.org/bot{}/".format(self.token)

        self.last_update = None
        self.command_queue = []

        self.queue_empty = True

        loop = threading.Thread(target=self.update_loop)
        loop.daemon = True
        loop.start()
        print("Done")


    def get_command(self):
        command = self.command_queue.pop(0)
        if not self.command_queue:
            self.queue_empty = True

        return DotMap(command)


    def update_loop(self):
        print("Starting Poll Update Loop")
        while True:
            self.poll_updates(self.last_update)
            

    def poll_updates(self, offset=None):
        try:
            url = self.URL + "getUpdates?timeout={}".format(self.poll_timeout)
            if offset:
                url += "&offset={}".format(offset)

            response = requests.get(url).content.decode("utf8")
            js = json.loads(response)["result"]
            self.command_queue.extend(js)
            self.last_update = max(x["update_id"] for x in js) + 1
            print("Poll Successful: {}".format(self.last_update))
            self.queue_empty = False
        except:
            pass



class NatsukoClient():


    def __init__(self, token):
        self.token = token
        self.poll_timeout = 100
        self.commands = {}

        self.APIL = "https://api.telegram.org/bot{}/".format(self.token)

        self.manager = None
        self.com_proc_running = False

        self.usercache = {}

    def run(self):
        self.manager = UpdateManager(token=self.token, callback=self.process, poll_timeout=100)
        self.process()


    def process(self):
        while True:

            while not self.manager.queue_empty:
                raw_command = self.manager.get_command()

                if "bot_command" in [x["type"] for x in raw_command.message.entities]:
                    # Gets the bot_command entity
                    e = [x for x in raw_command.message.entities if x["type"] == "bot_command"][0]
                    command = raw_command.message.text[e.offset + 1: e.offset + e.length]
                    print("Identified as Bot Command: {}".format(command))
                    if command in self.commands:
                        self.commands[command]["function"](Event(self, raw_command))


                if "message" in raw_command and not raw_command.message.keys():
                    if not raw_command.message["from"]["username"] in self.usercache:
                        self.usercache[raw_command.message["from"]["username"]] = raw_command.message["from"]

                elif "inline_query" in raw_command:
                    if not raw_command.inline_query["from"]["username"] in self.usercache:
                        self.usercache[raw_command.inline_query["from"]["username"]] = raw_command.inline_query["from"]

                elif "chat" in raw_command:
                    if not raw_command.chat["from"]["username"] in self.usercache:
                        self.usercache[raw_command.chat["from"]["username"]] = raw_command.chat["from"]

            
            time.sleep(0.5)


    # Command Decorator
    def command(self, name, **options):

        def deco(f):
            command = {"function": f}
            command["no_error"] = False if "no_error" not in options else options["no_error"]

            self.commands[name] = command
            print('\tLOAD_OK: {0.__name__}: on_command @ {1}'.format(f, name))

            return f
        return deco


    def api_gen(self, endpoint, **kwa):
        apiq = "{}{}?".format(self.APIL, endpoint)
        for arg, val in kwa.items():
            if val != None:
                apiq += "{}={}&".format(arg, val)
            elif type(val) is dict:
                apiq += "{}={}&".format(arg, urllib.parse.quote_plus(val))
        return apiq[:-1]


    def _api_send(self, apiq):
        print("APISEND: {}".format(apiq))
        response = requests.get(apiq)
        content = response.content.decode("utf8")
        content = json.loads(content)
        if not content["ok"]:
            raise APIError(content)
        return content["result"]


    def send_message(self, chat_id, message, **kwarg):
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
        message = urllib.parse.quote_plus(message)
        apiq = self.api_gen("sendMessage", 
                            text=message, 
                            chat_id=chat_id,
                            parse_mode=kwarg.get("parse_mode"),
                            disable_web_page_preview=kwarg.get("disable_web_page_preview"),
                            disable_notification=kwarg.get("disable_notification"),
                            reply_to_message_id=kwarg.get("reply"),
                            reply_markup=kwarg.get("reply_markup"))
        return self._api_send(apiq)


    def forward_message(self, target_cid, source_cid, 
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

        return self._api_send(apiq)


    def send_photo(self, chat_id, photo, **kwarg):
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
                                                        force a reply from the user."""
        caption = kwarg.get("caption")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(photo) is str and not photo.startswith("http"):
            apiq = self.api_gen("sendPhoto", 
                                chat_id=chat_id, 
                                photo=photo, 
                                caption=caption, 
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)
            return self._api_send(apiq)

        elif photo.startswith("http"):
            apiq = self.api_gen("sendPhoto", 
                                chat_id=chat_id, 
                                photo=urllib.parse.quote(photo), 
                                caption=caption, 
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)
            return self._api_send(apiq)

        else:
            apiq = self.api_gen("sendPhoto", 
                                chat_id=chat_id, 
                                caption=caption, 
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)

            response = requests.post(apiq, files=dict(photo=photo))
            return json.loads(response.content.decode("utf8"))


    def send_audio(self, chat_id, audio, **kwarg):
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
                                                        force a reply from the user."""
        caption = kwarg.get("caption")
        duration = kwarg.get("duration")
        performer = kwarg.get("performer")
        title = kwarg.get("title")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(audio) is str:
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
            return self._api_send(apiq)

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

            response = requests.post(apiq, files=dict(audio=audio))
            return response.content.decode("utf8")


    def send_document(self, chat_id, document, **kwarg):
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
                                                        force a reply from the user."""
        caption = kwarg.get("caption")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(document) is str:
            apiq = self.api_gen("sendDocument", 
                                chat_id=chat_id, 
                                document=document, 
                                caption=caption,
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)
            return self._api_send(apiq)

        else:
            apiq = self.api_gen("sendDocument", 
                                chat_id=chat_id, 
                                caption=caption,  
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)

            response = requests.post(apiq, files=dict(document=document))
            return response.content.decode("utf8")


    def send_video(self, chat_id, video, **kwarg):
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
                                                        force a reply from the user."""
        caption = kwarg.get("caption")
        duration = kwarg.get("duration")
        width = kwarg.get("width")
        height = kwarg.get("height")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(video) is str:
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
            return self._api_send(apiq)

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

            response = requests.post(apiq, files=dict(video=video))
            return response.content.decode("utf8")


    def send_voice(self, chat_id, voice, **kwarg):
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
                                                        force a reply from the user."""
        caption = kwarg.get("caption")
        duration = kwarg.get("duration")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(voice) is str:
            apiq = self.api_gen("sendVoice", 
                                chat_id=chat_id, 
                                voice=voice, 
                                caption=caption,
                                duration=duration,
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)
            return self._api_send(apiq)

        else:
            apiq = self.api_gen("sendVoice", 
                                chat_id=chat_id, 
                                caption=caption,
                                duration=duration, 
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)

            response = requests.post(apiq, files=dict(voice=voice))
            return response.content.decode("utf8")


    def send_video_note(self, chat_id, v_note, **kwarg):
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
                                                        force a reply from the user."""
        duration = kwarg.get("duration")
        disable_notification = kwarg.get("disable_notification")
        reply = kwarg.get("reply")
        reply_markup = kwarg.get("reply_markup")

        if type(v_note) is str:
            apiq = self.api_gen("sendVideoNote", 
                                chat_id=chat_id, 
                                video_note=video_note, 
                                duration=duration,
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)
            return self._api_send(apiq)

        else:
            apiq = self.api_gen("sendVideoNote", 
                                chat_id=chat_id, 
                                duration=duration, 
                                disable_notification=disable_notification, 
                                reply_to_message_id=reply, 
                                reply_markup=reply_markup)

            response = requests.post(apiq, files=dict(video_note=video_note))
            return response.content.decode("utf8")


    def send_location(self, chat_id, long_, lat, **kwarg):
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
                                                        force a reply from the user."""
        apiq = self.api_gen("sendLocation", 
                            chat_id=chat_id, 
                            latitude=lat, 
                            longitude=long_,
                            disable_notification=kwarg.get("disable_notification"), 
                            reply_to_message_id=kwarg.get("reply"), 
                            reply_markup=kwarg.get("reply_markup"))
        return self._api_send(apiq)


    def send_venue(self, chat_id, long_, title, address, lat, **kwarg):
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
                                                        force a reply from the user."""
        apiq = self.api_gen("sendVenue", 
                            chat_id=chat_id, 
                            latitude=lat, 
                            longitude=long_,
                            title=title,
                            address=address,
                            disable_notification=kwarg.get("disable_notification"),
                            foursquare_id=kwarg.get("foursquare_id"),  
                            reply_to_message_id=kwarg.get("reply"), 
                            reply_markup=kwarg.get("reply_markup"))
        return self._api_send(apiq)


    def send_contact(self, chat_id, phone_number, first_name, **kwarg):
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
                                                        force a reply from the user."""
        apiq = self.api_gen("sendVenue", 
                            chat_id=chat_id, 
                            phone_number=phone_number,
                            first_name=first_name,
                            last_name=kwarg.get("last_name"),
                            disable_notification=kwarg.get("disable_notification"), 
                            reply_to_message_id=kwarg.get("reply"), 
                            reply_markup=kwarg.get("reply_markup"))
        return self._api_send(apiq)


    def send_chat_action(self, chat_id, action):
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
        apiq = self.api_gen("sendChatAction",
                            chat_id=chat_id,
                            action=action)
        return self._api_send(apiq)


    def get_user_profile_photos(self, user_id, **kwarg):
        """Use this method to get a list of profile pictures for a user. 
        Returns a UserProfilePhotos Dictionary.
        (Optional parameters are keyword arguments)

        Parameters              Type        Required    Description
        user_id                 Int/Str     Yes         Unique identifier for the target user.
        offset                  Integer     Optional    Sequential number of the first photo to be returned. 
                                                        By default, all photos are returned.
        limit                   Integer     Optional    Limits the number of photos to be retrieved. 
                                                        Values between 1—100 are accepted. Defaults to 100"""
        apiq = self.api_gen("getUserProfilePhotos", 
                            user_id=user_id,
                            offset=kwarg.get("offset"),
                            limit=kwarg.get("limit"))
        result = self._api_send(apiq)["result"]
        return DotMap(result)


    def get_file(self, file_id):
        apiq = self.api_gen("getFile", 
                            file_id=file_id)
        result = self._api_send(apiq)
        return DotMap(result)


    def get_file_url(self, file_obj):
        return "https://api.telegram.org/file/bot{}/{}".format(self.token, file_obj.file_path)


    def ban_chat_memeber(self, chat_id, user_id, until_date=None):
        apiq = self.api_gen("kickChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            until_date=until_date)
        return self._api_send(apiq)


    def unban_chat_memeber(self, chat_id, user_id):
        apiq = self.api_gen("unbanChatMember",
                            chat_id=chat_id,
                            user_id=user_id)
        return self._api_send(apiq)


    def restrict_chat_memeber(self, chat_id, user_id, **kwarg):
        apiq = self.api_gen("restrictChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            until_date=kwarg.get("until_date"),
                            can_send_messages=kwarg.get("can_send_messages"),
                            can_send_media_messages=kwarg.get("can_send_media_messages"),
                            can_send_other_messages=kwarg.get("can_send_other_messages"),
                            can_add_web_page_previews=kwarg.get("can_add_web_page_previews"))
        return self._api_send(apiq)


    def promote_chat_memeber(self, chat_id, user_id, **kwarg):
        apiq = self.api_gen("promoteChatMember",
                            chat_id=chat_id,
                            user_id=user_id,
                            can_change_info=kwarg.get("can_change_info"),
                            can_post_messages=kwarg.get("can_post_messages"),
                            can_edit_messages=kwarg.get("can_edit_messages"),
                            can_delete_messages=kwarg.get("can_delete_messages"),
                            can_invite_users=kwarg.get("can_invite_users"),
                            can_restrict_users=kwarg.get("can_restrict_users"),
                            can_pin_messages=kwarg.get("can_pin_messages"),
                            can_promote_members=kwarg.get("can_promote_members"))
        return self._api_send(apiq)


    def export_invite_link(self, chat_id):
        apiq = self.api_gen("exportChatInviteLink",
                            chat_id=chat_id)
        return self._api_send(apiq)


    def set_chat_photo(self, chat_id, photo):
        apiq = self.api_gen("setChatPhoto",
                            chat_id=chat_id)

        response = requests.post(apiq, files=dict(photo=photo))
        return json.loads(response.content.decode("utf8"))


    def delete_chat_photo(self, chat_id):
        apiq = self.api_gen("deleteChatPhoto",
                            chat_id=chat_id)

        return self._api_send(apiq)


    def set_chat_title(self, chat_id, title):
        apiq = self.api_gen("setChatTitle",
                            chat_id=chat_id,
                            title=title)

        return self._api_send(apiq)


    def set_chat_description(self, chat_id, descrption):
        apiq = self.api_gen("setChatDescription",
                            chat_id=chat_id,
                            descrption=descrption)

        return self._api_send(apiq)


    def pin_chat_message(self, chat_id, message_id, **kwarg):
        apiq = self.api_gen("pinChatMessage",
                            chat_id=chat_id,
                            message_id=message_id,
                            disable_notification=kwarg.get("disable_notification"))


        return self._api_send(apiq)


    def unpin_chat_message(self, chat_id):
        apiq = self.api_gen("unpinChatMessage",
                            chat_id=chat_id)

        return self._api_send(apiq)


    def get_chat(self, chat_id):
        apiq = self.api_gen("getChat",
                            chat_id=chat_id)

        return self._api_send(apiq)


    def get_chat_administrators(self, chat_id):
        apiq = self.api_gen("getChatAdministrators",
                            chat_id=chat_id)

        return self._api_send(apiq)


    def get_chat_member_count(self, chat_id):
        apiq = self.api_gen("getChatMembersCount",
                            chat_id=chat_id)

        return self._api_send(apiq)


    def set_chat_member(self, chat_id, user_id):
        apiq = self.api_gen("getChatMember",
                            chat_id=chat_id,
                            user_id=user_id)

        return self._api_send(apiq)

