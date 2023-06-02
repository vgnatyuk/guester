import requests
from aiogram import Bot
from datetime import datetime
from dataclasses import dataclass
from time import sleep

from instagrapi import Client
from instagrapi.exceptions import UserNotFound

try:
    import env
except ImportError:
    print('You need to create "env.py" based on "env.example.py"')


@dataclass(frozen=True, slots=True)
class MediaMessage:
    chat_id: str
    media_type: str
    media: bytes
    caption: str
    parse_mode: str = "HTML"


class GuestBartending:
    def __init__(self):
        self.client = Client()
        self.client.logout()
        self.client.login(env.USERNAME, env.PASSWORD)
        self.user_id = str(self.client.user_id)
        self.bot = Bot(token=env.TELEGRAM_BOT_API_TOKEN)

    def get_user_id_by_username(self, username: str) -> str | None:
        try:
            return self.client.user_id_from_username(username)
        except UserNotFound:
            return None

    def follow_user(self, username: str):
        user_id = self.get_user_id_by_username(username)
        if user_id:
            return self.client.user_follow(user_id)
        return

    def get_user_media(self, username, only_stories: bool = True) -> list[MediaMessage]:
        """
        Get all media of the user by username.
        """
        user_id = self.get_user_id_by_username(username)
        today = datetime.today()
        stories = self.client.user_stories(user_id)
        messages_to_send = []
        print("start stories")
        for story in stories:
            self.add_message_to_queue(story, messages_to_send)

        if only_stories:
            return messages_to_send

        medias = self.client.user_medias(user_id, 3)
        print("start media")
        for media in medias:
            if media.taken_at.date() == today.date():
                self.add_message_to_queue(media, messages_to_send)

        return messages_to_send

    def add_message_to_queue(self, media_data, queue: list, message=None):
        sleep(1)  # нужно для того, чтобы инстаграм не ругался на слишком частые запросы

        media_url = media_data.video_url or media_data.thumbnail_url
        media_bytes = requests.get(media_url).content
        media_type = "video" if media_data.video_url else "photo"
        if message is None:
            message = media_data.caption_text

        queue.append(
            MediaMessage(
                chat_id=env.CHAT_ID,
                media_type=media_type,
                media=media_bytes,
                caption=message,
                parse_mode="HTML",
            )
        )

    def parse_following_accounts(self):
        following = list(self.client.user_following(self.user_id).keys())
        messages_to_send = []
        for user_id in following:
            medias = self.client.user_medias(user_id, 20)
            messages = self.parse_medias(medias)
            messages_to_send += messages
        self.send_messages(messages_to_send)

    def parse_medias(self, medias) -> list:
        messages_to_send = []
        for media in medias:
            post_text = media.caption_text
            for word in env.PATTERNS:
                if word in post_text:
                    message = self.decorate_message_for_telegram(media, post_text)
                    self.add_message_to_queue(media, messages_to_send, message)
        return messages_to_send

    def decorate_message_for_telegram(self, media, post_text):
        code = media.code
        profile_link = f"https://www.instagram.com/{media.user.username}/"
        profile_name = media.user.full_name
        if resources := media.resources:
            media = resources[0]
        post_link = f"https://www.instagram.com/p/{code}/"
        message = (
            f'<a href="{profile_link}"><b>{profile_name}</b></a>\n'
            f'<a href="{post_link}">Post</a>\n\n'
            f"{post_text}"
        )
        return message

    @staticmethod
    def get_chat_id():
        url = f"https://api.telegram.org/bot{env.TELEGRAM_BOT_API_TOKEN}/getUpdates"
        return requests.get(url).json()

    def parse_user_by_username(self, username):
        messages_to_send = self.get_user_media(username)
        self.send_messages(messages_to_send)

    def send_messages(self, messages_to_send: list[MediaMessage]):
        for message in messages_to_send:
            if message.media_type == "video":
                self.send_video(message)
            elif message.media_type == "photo":
                self.send_photo(message)
            else:
                raise Exception(f"unknown media type: {message.media_type}")

    def send_video(self, message: MediaMessage):
        self.bot.send_video(
            chat_id=message.chat_id,
            video=message.media,
            caption=message.caption,
            parse_mode=message.parse_mode,
        )

    def send_photo(self, message: MediaMessage):
        self.bot.send_photo(
            chat_id=message.chat_id,
            photo=message.media,
            caption=message.caption,
            parse_mode=message.parse_mode,
        )


if __name__ == "__main__":
    guest = GuestBartending()
    guest.parse_following_accounts()
