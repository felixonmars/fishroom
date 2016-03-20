#!/usr/bin/env python3
from marshmallow import Schema, fields, validate, ValidationError


class ChannelType(object):
    """\
    Channel Types
    """
    XMPP = "xmpp"
    IRC = "irc"
    Telegram = "telegram"
    Web = "web"
    API = "api"


class MessageType(object):
    """\
    Message Types
    """
    Text = "text"
    Photo = "photo"
    Sticker = "sticker"
    Location = "location"
    Audio = "audio"
    Video = "video"
    Animation = "animation"
    File = "file"
    Event = "event"
    Command = "command"


class Color(object):

    def __init__(self, fg: int, bg: int=None):
        self.fg = fg
        self.bg = bg

    def __repr__(self):
        return "<color: {}/{}>".format(self.fg, self.bg)


class ColorField(fields.Field):

    def _serialize(self, value, attr, obj):
        if value is None:
            return ''
        return (value.fg, value.bg)

    def _deserialize(self, value, attr, obj):
        if not value:
            return None
        elif isinstance(value, int):
            return Color(value)
        else:
            try:
                fg, bg = map(int, value)
            except:
                raise ValidationError(
                    "Color field should only contain fg and bg")
            return Color(fg, bg)
    # def __str__(self):
    #     return json.dumps({'fg': self.fg, 'bg': self.bg})


class TextStyle(object):

    NORMAL = 0
    COLOR = 1
    ITALIC = 2
    BOLD = 4
    UNDERLINE = 8

    _schema = None  # should be set later

    def __init__(self, color: Color=None, italic: int=0,
                 bold: int=0, underline: int=0, style: int=0):
        self.style = style
        if color:
            self.style |= self.COLOR
            self.color = color
        self.style |= self.ITALIC if italic else 0
        self.style |= self.BOLD if bold else 0
        self.style |= self.UNDERLINE if underline else 0

    @classmethod
    def style_list(cls, style):
        styles = []
        if style & cls.ITALIC:
            styles.append('italic')
        if style & cls.BOLD:
            styles.append('bold')
        if style & cls.UNDERLINE:
            styles.append('underline')
        return styles

    def dump(self):
        return self._schema.dump(self).data

    def dumps(self):
        return self._schema.dumps(self).data

    @classmethod
    def loads(cls, jstr):
        if isinstance(jstr, bytes):
            jstr = jstr.decode('utf-8')

        ts = TextStyle(**cls._schema.loads(jstr).data)
        return ts

    @classmethod
    def load(cls, data):
        return TextStyle(**cls._schema.load(data).data)

    def __repr__(self):
        styles = self.style_list(self.style)
        color = None
        if self.style & self.COLOR:
            color = self.color

        if color is None:
            if not styles:
                return "<normal>"
            return "<{}>".format(",".join(styles))

        if not styles:
            return "{}".format(self.color)
        return "<{}, [{}]>".format(self.color, ",".join(styles))


class TextStyleField(fields.Field):

    def _serialize(self, value, attr, obj):
        if value is None:
            return []
        return TextStyle.style_list(value)

    def _deserialize(self, value, attr, obj):
        style = TextStyle.NORMAL
        try:
            styles = set(value)
        except:
            raise ValidationError("Invalid style list")
        if "italic" in styles:
            style |= TextStyle.ITALIC
        if "bold" in styles:
            style |= TextStyle.BOLD
        if "underline" in styles:
            style |= TextStyle.UNDERLINE
        return style


class TextStyleSchema(Schema):

    color = ColorField(missing=None)
    style = TextStyleField(missing=[])


TextStyle._schema = TextStyleSchema()


class RichTextField(fields.Field):

    def _serialize(self, value, attr, obj):
        if value is None:
            return None

        try:
            for style, text in value:
                if not isinstance(style, TextStyle) or \
                        not isinstance(text, str):
                    raise
        except:
            raise ValidationError(
                "RichText should be a list of style and content")

        return [(s.dump(), t) for s, t in value]

    def _deserialize(self, value, attr, obj):
        if value is None:
            return None
        try:
            return [(TextStyle.load(s), t) for s, t in value]
        except:
            raise ValidationError(
                "RichText should be a list of style and content")


class MessageSchema(Schema):
    """\
    Json Schema for Message
    """

    # Where is this message from
    channel = fields.String()
    # message sender
    sender = fields.String()
    # message receiver (usually group id)
    receiver = fields.String()
    # message type
    mtype = fields.String(validate=validate.OneOf(
        (MessageType.Photo, MessageType.Text, MessageType.Sticker,
         MessageType.Location, MessageType.Audio, MessageType.Command,
         MessageType.Event, MessageType.File, MessageType.Animation,
         MessageType.Video),
    ))
    # if message is photo or sticker, this contains url
    media_url = fields.String()
    # message text
    content = fields.String()
    # formated rich text
    rich_text = RichTextField()
    # date and time
    date = fields.String()
    time = fields.String()
    # is this message from fishroom bot?
    botmsg = fields.Boolean()
    # room
    room = fields.String()
    # channel specific options (passed to send_msg method)
    opt = fields.Dict()


class Message(object):
    """\
    Message instance

    Attributes:
        channel: one in ChannelType.{XMPP, Telegram, IRC}
        sender: sender name
        receiver: receiver name
        content: message content
        mtype: text or photo or sticker
        media_url: URL to media if mtype is sticker or photo
        date, time: message date and time
        room: which room to deliver
        botmsg: msg is from fishroom bot
        opt: channel specific options
    """

    _schema = MessageSchema()

    def __init__(self, channel, sender, receiver, content,
                 mtype=MessageType.Text, date=None, time=None,
                 media_url=None, botmsg=False, room=None, opt=None,
                 rich_text=None):
        self.channel = channel
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.rich_text = rich_text
        self.mtype = mtype
        self.date = date
        self.time = time
        self.media_url = media_url
        self.botmsg = botmsg
        self.room = room
        self.opt = opt or {}

    def __repr__(self):
        return (
            "[{channel}] {mtype} from: {sender}, to: {receiver}, {content}"
            .format(
                channel=self.channel, mtype=self.mtype, sender=self.sender,
                receiver=self.receiver, content=self.content,
            ))

    def dumps(self):
        return self._schema.dumps(self).data

    @classmethod
    def loads(cls, jstr):
        if isinstance(jstr, bytes):
            jstr = jstr.decode('utf-8')

        try:
            m = Message(**cls._schema.loads(jstr).data)
            return m
        except:
            return Message("fishroom", "fishroom", "None", "Error")


if __name__ == '__main__':

    c = Color(fg=5, bg=6)
    ts = TextStyle(color=c, italic=1)
    print(TextStyle.loads(ts.dumps()))

    m = Message(
        channel=ChannelType.Telegram, content="test", sender="tester",
        receiver="tester2", rich_text=[(ts, "test")])
    m = Message.loads(m.dumps())
    print(m, m.rich_text)


# vim: ts=4 sw=4 sts=4 expandtab
