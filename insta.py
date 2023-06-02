from collections import namedtuple

import asyncio
import requests
from aiogram import Bot
from datetime import datetime
from dataclasses import dataclass
from time import sleep
from typing import Union, List

from instagrapi import Client
from instagrapi.exceptions import UserNotFound

from env import *


@dataclass(frozen=True, slots=True) # todo frozen, slots?
class MediaMessage:
    chat_id: str
    media_type: str
    media: bytes
    caption: str
    parse_mode: str = 'HTML'

# MediaMessage = namedtuple(
#     'MediaMessage',
#     [
#         'chat_id',
#         'media_type',
#         'media',
#         'caption',
#         'parse_mode',
#     ]
# )


class GuestBartending:
    def __init__(self):
        self.client = Client()
        self.client.logout()
        self.client.login(USERNAME, PASSWORD)
        self.user_id = self.client.user_id
        self.bot = Bot(token=BOT_API_TOKEN)

    def get_user_id_by_username(self, username: str) -> Union[str, None]:
        try:
            return self.client.user_id_from_username(username)
        except UserNotFound:
            return None

    def follow_user(self, username: str):
        user_id = self.get_user_id_by_username(username)
        if user_id:
            return self.client.user_follow(user_id)
        return

    async def get_user_media(self, username: str='holodoz', only_stories: bool=True) -> List[MediaMessage]:
        """
        Get all media of the user by username.

        :param username:
        :param only_stories:
        :return:
        """
        user_id = self.get_user_id_by_username(username)
        today = datetime.today()
        stories = self.client.user_stories(user_id)
        messages_to_send = []
        print('start stories')
        for story in stories:
            self.add_message_to_queue(story, messages_to_send)

        if only_stories:
            return messages_to_send

        medias = self.client.user_medias(user_id, 3)
        print('start media')
        for media in medias:
            if media.taken_at.date() == today.date():
            # self.bot.send_media_group(chat_id=CHAT_ID)
                self.add_message_to_queue(media, messages_to_send)


        return messages_to_send

    def add_message_to_queue(self, media_data, queue: list, message=None):
        sleep(1)

        media_url = media_data.video_url or media_data.thumbnail_url
        media_bytes = requests.get(media_url).content
        media_type = 'video' if media_data.video_url else 'photo'
        if message is None:
            message = media_data.caption_text

        queue.append(MediaMessage(
            chat_id=CHAT_ID,
            media_type=media_type,
            media=media_bytes,
            caption=message,
            parse_mode='HTML',
        ))

        # media_bytes = requests.get(media_url).content
        # # await self.bot.send_message(CHAT_ID, message, parse_mode='HTML')  # like this
        # if media.video_url:
        #     await self.bot.send_video(chat_id=CHAT_ID, video=media_bytes,
        #                               caption=message, parse_mode='HTML')
        # else:
        #     await self.bot.send_photo(chat_id=CHAT_ID, photo=media_bytes,
        #                               caption=message, parse_mode='HTML')
        # print('send to telegram')
        # return


        # if media.video_url:
        #     await self.bot.send_video(chat_id=CHAT_ID, video=media_bytes,
        #                               caption=message, parse_mode='HTML')
        # else:
        #     await self.bot.send_photo(chat_id=CHAT_ID, photo=media_bytes,
        #                               caption=message, parse_mode='HTML')

    async def parse_following_accounts(self):
        following = list(self.client.user_following(self.user_id).keys())
        messages_to_send = []
        for user_id in following:
            print(user_id)
            # if int(user_id) == 438392382:
            #     continue
            medias = self.client.user_medias(user_id, 20)
            for media in medias:
            # for media in medias[7:8]:
                post_text = media.caption_text
                for word in PATTERNS:
                    if word in post_text:
                        message = self.decorate_message_for_telegram(media, post_text)
                        self.add_message_to_queue(media, messages_to_send, message)
        self.send_messages(messages_to_send)

                    # print(media.video_url)
                    # print(media.thumbnail_url)
                    # message = f'<a href="{message}">inline URL</a>'
                    # url = f"https://api.telegram.org/bot{BOT_API_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
                    # return


    def decorate_message_for_telegram(self, media, post_text):
        # self.client.user_info(user_id).category todo то что указано в аккаунте, у Фрески "Bar"
        code = media.code
        profile_link = f'https://www.instagram.com/{media.user.username}/'
        profile_name = media.user.full_name
        if resources := media.resources:
            media = resources[0]
        media_url = media.video_url or media.thumbnail_url
        post_link = f'https://www.instagram.com/p/{code}/'
        message = (
            # f'<a href="{media_url}">{emoji}</a>\n'
            f'<a href="{profile_link}"><b>{profile_name}</b></a>\n'
            f'<a href="{post_link}">Post</a>\n\n'
            f'{post_text}'
        )
        return message



    @staticmethod
    def get_chat_id():
        url = f"https://api.telegram.org/bot{BOT_API_TOKEN}/getUpdates"
        return requests.get(url).json()

    async def parse_user_by_username(self, username: str='holodoz'):
        print('start')
        messages_to_send = await self.get_user_media(username)
        self.send_messages(messages_to_send)

    def send_messages(self, messages_to_send: List[MediaMessage]):
        for message in messages_to_send:
            if message.media_type == 'video':
                self.send_video(message)
            elif message.media_type == 'photo':
                self.send_photo(message)
            else:
                raise Exception(f'unknown media type: {message.media_type}')

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

if __name__ == '__main__':
    guest = GuestBartending()
    # print(guest.get_chat_id())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(guest.parse_user_by_username()) # todo
    # loop.run_until_complete(guest.parse_following_accounts())
    loop.close()
