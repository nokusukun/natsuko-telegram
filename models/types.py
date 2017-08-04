

class MasterType():

    def __init__(self, client, data):

        self.TYPE_MAP = {
            'user':                 ('user', User),

            'message':              ('message', Message),
            'from':                 ('author', User),
            'chat':                 ('chat', Chat),
            'forward_from':         ('forward_from', User),
            'forward_from_chat':    ('forward_from_chat', Chat),
            'reply_to_message':     ('reply_to', Message),
            'audio':                ('audio', Audio),
            'document':             ('document', Document),
            'game':                 ('game', Game),
            'photo':                ('photo', PhotoSize),
            'sticker':              None,
            'video':                ('video', Video),
            'voice':                ('voice', Voice),
            'video_note':           ('video_note', VideoNote),
            'new_chat_members':     None,
            'contact':              ('contact', Contact),
            'location':             ('location', Location),
            'venue':                ('venue', Venue),
            'new_chat_member':      ('new_chat_member', User),
            'left_chat_member':     ('left_chat_member', User),
            'new_chat_photo':       ('new_chat_photo', PhotoSize),
            'pinned_message':       ('pinned_message', Message),
            'invoice':              None,
            'successful_payment':   None
        }


        self.client = client
        self.data = data

        for attr in data:
            self._add_attribute(attr)


    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return None

    def _add_attribute(self, attr):

        if attr not in self.TYPE_MAP:
            self.__dict__[attr] = self.data.get(attr)

        else:
            _attr = self.TYPE_MAP[attr]
            if isinstance(_attr, tuple):
                _type = self.TYPE_MAP[attr][0]
                _value = self.TYPE_MAP[attr][1]
            else:
                _type = attr
                _value = self.TYPE_MAP[attr]

            if isinstance(_value, type):
                _data = self.data.get(attr)
                _value = _value(self.client, _data)

            self.__dict__[_type] = _value


    def __str__(self):
        d = ", ".join([f"{x}={self.__dict__[x]}" for x in self.__slots__ if x in self.__dict__])
        t = str(type(self))[8:-2]
        return f'<{t}>: ({d})'


class Event(MasterType):

    __slots__ = ['message', 'update_id', 'chat', 'raw_event']

    def __init__(self, client, event):
        super().__init__(client, event)

        self.chat = self.message.chat
        self.raw_event = event


class Message(MasterType):
    '''
    This object represents a message.
    '''

    __slots__ = ['message_id', 'author', 'date', 'chat', 'forward_from', 'forward_from_chat',
                 'forward_from_message_id', 'forward_date', 'reply_to_message', 'edit_date',
                 'text', 'entities', 'audio', 'document', 'game', 'photo', 'sticker', 'video',
                 'voice', 'video_note', 'new_chat_members', 'caption', 'contact', 'location',
                 'venue', 'new_chat_member', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                 'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
                 'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id',
                 'pinned_message', 'invoice', 'successful_payment']


    def __init__(self, client, data):
        super().__init__(client, data)

        self.entities = [MessageEntity(client, self.text, e) for e in self.data.entities]
        self.id = self.message_id


    @property
    def mentions(self):
        mentions = []
        for entity in self.entities:
            if entity.type == 'mention':
                self._mentions.append(entity)
        return mentions

    @property
    def commands(self):
        commands = []
        for entity in self.entities:
            if entity.type == 'bot_command':
                commands.append(entity)
        return commands


    # could this be a generator?
    def get_entities(self, t):
        return [x.text for x in self.entities if x.type == t]

    async def forward(self, chat_id):
        return await self.client.forward_message(chat_id, self.chat.id, self.message.message_id)



class MessageEntity(MasterType):
    '''
    This object represents one special entity in a text message. For example, hashtags, usernames, URLs, etc.
    '''

    __slots__ = ['text', 'type', 'offset', 'length', 'clean_text']

    def __init__(self, client, text, data):
        super().__init__(client, data)

        self.text = text[self.offset: self.offset + self.length]
        self.clean_text = self.text[1:]


class Chat(MasterType):
    '''
    This object represents a chat.
    '''

    __slots__ = ['id', 'type', 'title', 'username', 'first_name', 'last_name',
                 'all_members_are_administrators', 'photo', 'description',
                 'invite_link']

    def __init__(self, client, data):
        super().__init__(client, data)


    async def send_message(self, message, **kwargs):
        # reply and reply_photo could probably be a single
        # method, with an if type()...I think
        return await self.client.send_message(self.id, message)

    async def forward_message(self, chat_id, message_id, **kwargs):
        return await self.client.forward_message(self.id, chat_id, message_id)

    async def send_sticker(self, sticker, **kwargs):
        return await self.client.send_sticker(self.id, sticker.file_id)

    async def send_photo(self, photo, **kwargs):
        return await self.client.send_photo(self.id, photo, **kwargs)

    async def get_member(self, user_id):
        data = self.client.get_chat_member(self.id, user_id)
        member = ChatMember(self.client, data)

        return member




class User(MasterType):
    '''
    This object represents a Telegram user or bot.
    '''

    __slots__ = ['id', 'first_name', 'last_name', 'username', 'language_code']

    def __init__(self, client, data):
        super().__init__(client, data)


class PhotoSize(MasterType):
    '''
    This object represents one size of a photo or a file / sticker thumbnail.
    '''

    __slots__ = ['id', 'width', 'height', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Audio(MasterType):
    '''
    This object represents an audio file to be treated as music by the Telegram clients.
    '''

    __slots__ = ['file_id', 'duration', 'performer', 'title', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)



class Document(MasterType):
    '''
    This object represents a general file (as opposed to photos, voice messages and audio files).
    '''

    __slots__ = ['file_id', 'thumb', 'file_name', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)

class Game(MasterType):
    '''
    This object represents a game. Use BotFather to create and edit games, their short names will act as unique identifiers.
    '''

    __slots__ = ['title', 'description', 'photo', 'text', 'text_entities', 'animation']

    def __init__(self, client, data):
        super().__init__(client, data)

class Video(MasterType):
    '''
    This object represents a video file.
    '''

    __slots__ = ['file_id', 'width', 'height', 'duration', 'thumb', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Voice(MasterType):
    '''
    This object represents a voice note.
    '''

    __slots__ = ['file_id', 'duration', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)



class VideoNote(MasterType):
    '''
    This object represents a video message (available in Telegram apps as of v.4.0).
    '''

    __slots__ = ['file_id', 'length', 'duration', 'thumb', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Sticker(MasterType):
    '''
    This object represents a sticker.
    '''

    __slots__ = ['file_id', 'width', 'height', 'thumb', 'emoji', 'set_name', 'mask_position', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class StickerSet(MasterType):
    '''
    This object represents a sticker set.
    '''

    __slots__ = ['name', 'title', 'contains_masks', 'stickers']

    def __init__(self, client, data):
        super().__init__(client, data)
        self.stickers = [Sticker(client, x) for x in self.stickers]


class Contact(MasterType):
    '''
    This object represents a phone contact.
    '''

    __slots__ = ['phone_number', 'first_name', 'last_name', 'user_id']

    def __init__(self, client, data):
        super().__init__(client, data)



class Location(MasterType):
    '''
    This object represents a point on the map.
    '''

    __slots__ = ['longitude', 'latitude']

    def __init__(self, client, data):
        super().__init__(client, data)



class Venue(MasterType):
    '''
    This object represents a venue.
    '''

    __slots__ = ['location', 'title', 'address', 'foursquare_Id']

    def __init__(self, client, data):
        super().__init__(client, data)



class UserProfilePhotos(MasterType):
    '''
    This object represent a user's profile pictures.
    '''

    __slots__ = ['total_count', 'photos']

    def __init__(self, client, data):
        super().__init__(client, data)


class File(MasterType):
    '''
    This object represents a file ready to be downloaded.
    The file can be downloaded via the link https://api.telegram.org/file/bot<token>/<file_path>.
    It is guaranteed that the link will be valid for at least 1 hour. When the link expires,
    a new one can be requested by calling getFile.
    '''

    __slots__ = ['file_id', 'file_size', 'file_path']

    def __init__(self, client, data):
        super().__init__(client, data)


class ReplyKeyboardMarkup(MasterType):
    '''This object represents a custom keyboard with reply options'''

    __slots__ = ['keyboard', 'resize_keyboard', 'one_time_keyboard', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)



class KeyboardButton(MasterType):
    '''
    This object represents one button of the reply keyboard.
    For simple text buttons String can be used instead of this object to specify text of the button.
    Optional fields are mutually exclusive.
    '''

    __slots__ = ['text', 'request_contact', 'request_location']

    def __init__(self, client, data):
        super().__init__(client, data)



class ReplyKeyboardRemove(MasterType):
    '''
    Upon receiving a message with this object,
    Telegram clients will remove the current custom keyboard and display the default letter-keyboard.
    By default, custom keyboards are displayed until a new keyboard is sent by a bot.
    An exception is made for one-time keyboards that are hidden immediately after the user presses a button.
    '''

    __slots__ = ['remove_keyboard', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)


class InlineKeyboardMarkup(MasterType):
    '''
    This object represents an inline keyboard that appears right next to the message it belongs to.
    '''

    __slots__ = ['inline_keyboard']

    def __init__(self, client, data):
        super().__init__(client, data)


class InlineKeyboardButton(MasterType):
    '''
    This object represents one button of an inline keyboard. You must use exactly one of the optional fields.
    '''

    __slots__ = ['text', 'url', 'callback_data', 'switch_inline_query',
                 'switch_inline_query_current_chat', 'callback_game', 'pay']

    def __init__(self, client, data):
        super().__init__(client, data)


class CallbackQuery(MasterType):
    '''
    This object represents an incoming callback query from a callback button in an inline keyboard.
    If the button that originated the query was attached to a message sent by the bot, the field message will be present.
    If the button was attached to a message sent via the bot (in inline mode), the field inline_message_id will be present.
    Exactly one of the fields data or game_short_name will be present.
    '''

    __slots__ = ['id', 'from', 'message', 'inline_message_id', 'chat_instance',
                 'data', 'game_short_name']

    def __init__(self, client, data):
        super().__init__(client, data)


class ForcedReply(MasterType):
    '''
    Upon receiving a message with this object,
    Telegram clients will display a reply interface to the user (act as if the user has selected the bot‘s message and tapped ’Reply').
    This can be extremely useful if you want to create user-friendly step-by-step interfaces without having to sacrifice privacy mode.
    '''

    __slots__ = ['forced_reply', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)


class ChatPhoto(MasterType):
    '''
    This object represents a chat photo.
    '''

    __slots__ = ['small_file_id', 'big_file_id']

    def __init__(self, client, data):
        super().__init__(client, data)


class ChatMember(MasterType):
    '''
    This object contains information about one member of a chat.
    '''

    __slots__ = ['user', 'status', 'until_date', 'can_be_edited', 'can_change_photo',
                 'can_post_messages', 'can_edit_messages', 'can_invite_users', 'can_restrict_mmebers',
                 'can_pin_messages', 'can_promote_uesrs', 'can_send_messages', 'can_send_media_messages',
                 'can_send_other_messages', 'can_add_web_page_previews']

    def __init__(self, client, data):
        super().__init__(client, data)


class ResponseParameters(MasterType):
    '''
    Contains information about why a request was unsuccessfull.
    '''

    __slots__ = ['migrate_to_chat_id', 'reply_after']

    def __init__(self, client, data):
        super().__init__(client, data)


class InputFile(MasterType):
    '''
    This object represents the contents of a file to be uploaded.
    Must be posted using multipart/form-data in the usual way that files are uploaded via the browser.
    '''

    __slots__ = ['chat_id', 'text', 'parse_mode', 'disable_web_page_preview',
                 'disable_notification', 'reply_to_message_id', 'reply_markup']

    def __init__(self, client, data):
        super().__init__(client, data)


