import unittest
from pyrogram.enums import MessageEntityType, MessageMediaType
from pyrogram.types import Message, Dice, Poll, Game, Story, MessageEntity
from tgc.pyro.convert import convert_media_dict, entity_start_end
from tgc.pyro.crawl import effective_text
from hypy_utils import json_stringify


class TestNewMessageTypes(unittest.TestCase):
    def test_dice_message(self):
        dice = Dice(emoji="🎲", value=6)
        msg = Message(id=1, dice=dice, media=MessageMediaType.DICE)
        d = convert_media_dict(msg)
        self.assertEqual(d.get("emoji"), "🎲")
        self.assertEqual(d.get("value"), 6)
        self.assertEqual(d.get("media_type"), "dice")
        self.assertIsNone(effective_text(msg))

    def test_poll_effective_text(self):
        poll = Poll(id="1", question="What is your favorite color?", total_voter_count=10, is_closed=False, is_anonymous=True, type="regular", allows_multiple_answers=False, options=[])
        msg = Message(id=2, poll=poll, media=MessageMediaType.POLL)
        self.assertEqual(effective_text(msg), "What is your favorite color?")

    def test_game_message(self):
        game = Game(id=1, short_name="lumberjack", title="Lumberjack", description="Chop trees", photo=None)
        msg = Message(id=3, game=game, media=MessageMediaType.GAME)
        d = convert_media_dict(msg)
        self.assertEqual(d.get("title"), "Lumberjack")
        self.assertEqual(d.get("media_type"), "game")
        self.assertIn("Lumberjack", effective_text(msg))

    def test_new_entities(self):
        # CASHTAG
        en_cashtag = MessageEntity(type=MessageEntityType.CASHTAG, offset=0, length=4)
        start, end = entity_start_end("$TON", en_cashtag)
        self.assertIn("t.me/share/url", start)

        # BOT_COMMAND
        en_cmd = MessageEntity(type=MessageEntityType.BOT_COMMAND, offset=0, length=6)
        start, end = entity_start_end("/start", en_cmd)
        self.assertEqual(start, "<code>")
        self.assertEqual(end, "</code>")

        # EMAIL
        email_str = "test@example.com"
        en_email = MessageEntity(type=MessageEntityType.EMAIL, offset=0, length=len(email_str))
        start, end = entity_start_end(email_str, en_email)
        self.assertEqual(start, '<a href="mailto:test@example.com">')

        # PHONE_NUMBER
        en_phone = MessageEntity(type=MessageEntityType.PHONE_NUMBER, offset=0, length=12)
        start, end = entity_start_end("+1234567890", en_phone)
        self.assertEqual(start, '<a href="tel:+1234567890">')

        # BANK_CARD
        en_card = MessageEntity(type=MessageEntityType.BANK_CARD, offset=0, length=16)
        start, end = entity_start_end("1234567812345678", en_card)
        self.assertEqual(start, "<code>")


if __name__ == "__main__":
    unittest.main()
