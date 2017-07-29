
from dotmap import DotMap
from pprint import pprint



class MasterType():

    def __init__(self, client, data, data_map=None):

        self.client = client
        self.data = data

        for attr in data:
            self._add_attribute(attr, data_map)


    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return None

    def _add_attribute(self, attr, data_map):

        if data_map and attr in data_map:
            # if map provides (attr, function) or (attr, class)
            if isinstance(data_map[attr], tuple):
                _attr = data_map[attr][0]

                # if the map provides a class
                if isinstance(data_map[attr][1], type):
                    _cls = data_map[attr][1]
                    _data = self.data.get(attr)
                    self.__dict__[_attr] = _cls(self.client, _data)
                else:
                    _data = data_map[attr][1]
                    self.__dict__[_attr] = _data

            # if simply aliasing old_attr -> new_attr
            elif isinstance(data_map[attr], str):
                _attr = data_map[attr]
                _data = self.data.get(attr)
                self.__dict__[_attr] = _data

        else:
            self.__dict__[attr] = self.data.get(attr)

    def __str__(self):
        d = ", ".join([f"{x}={self.__dict__[x]}" for x in self.__slots__ if x in self.__dict__])
        t = str(type(self))[8:-2]
        return f'<{t}>: ({d})'


class Event(MasterType):

    __slots__ = ['message', 'update_id', 'chat', 'raw_event']

    def __init__(self, client, event):

        data_map = {"message": ("message", Message)}
        super().__init__(client, event, data_map)

        self.chat = self.message.chat
        self.raw_event = event


class Message(MasterType):

    __slots__ = ['message_id', 'user', 'date', 'chat', 'forward_from', 'forward_from_chat',
                 'forward_from_message_id', 'forward_date', 'reply_to_message', 'edit_date',
                 'text', 'entities', 'audio', 'document', 'game', 'photo', 'sticker', 'video',
                 'voice', 'video_note', 'new_chat_members', 'caption', 'contact', 'location',
                 'venue', 'new_chat_member', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                 'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
                 'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id',
                 'pinned_message', 'invoice', 'successful_payment']


    def __init__(self, client, data):

        data_map = {"from": ("user", User),
                    "chat": ("chat", Chat)}
        super().__init__(client, data, data_map)

        self.entities = [MessageEntity(client, self.text, e) for e in self.data.entities]
        self.id = self.message_id


    # could this be a generator?
    def get_entities(self, t):
        return [x.text for x in self.entities if x.type == t]

    async def forward(self, chat_id):
        return await self.client.forward_message(chat_id, self.chat.id, self.message.message_id)



class MessageEntity(MasterType):

    __slots__ = ['text', 'type', 'offset', 'length', 'bot_command', 'clean_text']

    def __init__(self, client, text, data):
        super().__init__(client, data)

        self.text = text[self.offset: self.offset + self.length]
        self.clean_text = self.text[1:]
        self.bot_command = self.type == 'bot_command'


class Chat(MasterType):

    __slots__ = ['id', 'type', 'title', 'username', 'first_name', 'last_name',
                 'all_members_are_administrators', 'photo', 'description',
                 'invite_link']

    def __init__(self, client, data):
        super().__init__(client, data)


    async def send_message(self, message):
        # reply and reply_photo could probably be a single
        # method, with an if type()...I think

        return await self.client.send_message(self.id, message)

    async def reply_photo(self, photo):
        return await self.client.send_photo(self.id, photo)



class User(MasterType):

    __slots__ = ['id', 'first_name', 'last_name', 'username', 'language_code']

    def __init__(self, client, data):
        super().__init__(client, data)


class PhotoSize(MasterType):

    __slots__ = ['id', 'width', 'height', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Audio(MasterType):

    __slots__ = ['file_id', 'duration', 'performer', 'title', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)



class Document(MasterType):

    __slots__ = ['file_id', 'thumb', 'file_name', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Video(MasterType):

    __slots__ = ['file_id', 'width', 'height', 'duration', 'thumb', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)


class Voice(MasterType):

    __slots__ = ['file_id', 'duration', 'mime_type', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)



class VideoNote(MasterType):

    __slots__ = ['file_id', 'length', 'duration', 'thumb', 'file_size']

    def __init__(self, client, data):
        super().__init__(client, data)



class Contact(MasterType):

    __slots__ = ['phone_number', 'first_name', 'last_name', 'user_id']

    def __init__(self, client, data):
        super().__init__(client, data)



class Location(MasterType):

    __slots__ = ['longitude', 'latitude']

    def __init__(self, client, data):
        super().__init__(client, data)



class Venue(MasterType):

    __slots__ = ['location', 'title', 'address', 'foursquare_Id']

    def __init__(self, client, data):
        super().__init__(client, data)



class UserProfilePhotos(MasterType):

    __slots__ = ['total_count', 'photos']

    def __init__(self, client, data):
        super().__init__(client, data)


class File(MasterType):

    __slots__ = ['file_id', 'file_size', 'file_path']

    def __init__(self, client, data):
        super().__init__(client, data)


class ReplyKeyboardMarkup(MasterType):

    __slots__ = ['keyboard', 'resize_keyboard', 'one_time_keyboard', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)



class KeyboardButton(MasterType):

    __slots__ = ['text', 'request_contact', 'request_location']

    def __init__(self, client, data):
        super().__init__(client, data)



class ReplyKeyboardRemove(MasterType):

    __slots__ = ['remove_keyboard', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)


class InlineKeyboardMarkup(MasterType):

    __slots__ = ['inline_keyboard']

    def __init__(self, client, data):
        super().__init__(client, data)


class InlineKeyboardButton(MasterType):

    __slots__ = ['text', 'url', 'callback_data', 'switch_inline_query',
                 'switch_inline_query_current_chat', 'callback_game', 'pay']

    def __init__(self, client, data):
        super().__init__(client, data)


class CallbackQuery(MasterType):

    __slots__ = ['id', 'from', 'message', 'inline_message_id', 'chat_instance',
                 'data', 'game_short_name']

    def __init__(self, client, data):
        super().__init__(client, data)


class ForcedReply(MasterType):

    __slots__ = ['forced_reply', 'selective']

    def __init__(self, client, data):
        super().__init__(client, data)


class ChatPhoto(MasterType):

    __slots__ = ['small_file_id', 'big_file_id']

    def __init__(self, client, data):
        super().__init__(client, data)


class ChatMember(MasterType):

    __slots__ = ['user', 'status', 'until_date', 'can_be_edited', 'can_change_photo',
                 'can_post_messages', 'can_edit_messages', 'can_invite_users', 'can_restrict_mmebers',
                 'can_pin_messages', 'can_promote_uesrs', 'can_send_messages', 'can_send_media_messages',
                 'can_send_other_messages', 'can_add_web_page_previews']

    def __init__(self, client, data):
        super().__init__(client, data)


class ResponseParameters(MasterType):

    __slots__ = ['migrate_to_chat_id', 'reply_after']

    def __init__(self, client, data):
        super().__init__(client, data)


class InputFile(MasterType):

    __slots__ = ['chat_id', 'text', 'parse_mode', 'disable_web_page_preview',
                 'disable_notification', 'reply_to_message_id', 'reply_markup']

    def __init__(self, client, data):
        super().__init__(client, data)


