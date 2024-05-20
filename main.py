import json
from tqdm import tqdm
import requests
from datetime import datetime
import os
from decouple import config

VK_TOKEN = config('VK_TOKEN', default='')
YA_TOKEN = config('YA_TOKEN', default='')

# создаем класс для работы с ВК
class VK:
    def __init__(self, access_token, version='5.131'):
        self.token = access_token
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

# получаем id пользователя в виде числа

    def users_info(self, owner_id):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': owner_id}
        response = requests.get(url, params={**self.params, **params})
        if len(response.json()['response']) > 0:
            owner_id = response.json()['response'][0]['id']
            return owner_id
        else:
            print('Ошибка: пользователь не найден')


# получаем информацию о всех фото профиля пользователя
    def get_profile_photos(self, owner_id):
        owner_id = self.users_info(owner_id)
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': owner_id, 'album_id': 'profile', 'extended': 1}
        if owner_id:
            response = requests.get(url, params={**self.params, **params})
            all_photos_info = response.json()['response']['items']
            return all_photos_info

# переводим дату в понятный формат

    def convert_time(self, unixtime):
        date = str(datetime.fromtimestamp(unixtime))
        return date.split()[0]

# собираем информацию о фото

    def get_photo_info(self, photo):
        photo_url = photo['sizes'][-1]['url']
        likes = photo['likes']['count']
        date = self.convert_time(photo['date'])
        height = photo['sizes'][-1]['height']
        width = photo['sizes'][-1]['width']
        return photo_url, likes, date, height, width


# скачиваем фографии в нужном размере и с нужным названием, сохраняем информацию в json
# также сохраняем только последние N фотографий

    def download_photos(self, owner_id, num=5, folder_name='profile photos'):
        photos = self.get_profile_photos(owner_id)[::-1]
        photos = tqdm(photos[:num], ncols=100, desc='Скачивание фотографий...')
        os.mkdir(folder_name)
        photos_info = {'photos': []}
        for photo in photos:
            photo_url, likes, date, height, width = self.get_photo_info(photo)
            response = requests.get(photo_url)
            if os.path.isfile(str(likes)):
                file_name = f'{likes} {date}'
            else:
                file_name = str(likes)
            name = os.path.join(folder_name, file_name)
            photos_info['photos'].append({'name': f'{file_name}.jpg', 'height': height, 'width': width})
            with open(name, 'wb') as file:
                file.write(response.content)
        with open('photos_info.json', 'w') as f:
            json.dump(photos_info, f, ensure_ascii=False, indent=2)
        return folder_name

# создаем папку на Яндекс.Диске

    def create_folder(self, folder_name, token):
        params = {'path': folder_name}
        headers = {'Authorization': f'OAuth {token}'}
        response = requests.put('https://cloud-api.yandex.net/v1/disk/resources', params=params, headers=headers)

# функция для загрузки на диск

    def upload_photos(self, folder_name, file_name, token):
        params = {'path': f'{folder_name}/{file_name}'}
        headers = {'Authorization': f'OAuth {token}'}
        response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/upload', params=params, headers=headers)
        url_for_upload = response.json()['href']
        with open(f'profile photos/{file_name}', 'rb') as content:
            requests.put(url_for_upload, files={'file': content})
        os.remove(f'profile photos/{file_name}')

# загружаем фото из папки на Яндекс.Диск:

    def find_and_upload(self, owner_id, folder_name, token):
        folder = self.download_photos(owner_id)
        files = os.listdir(folder)
        for file_name in tqdm(files, ncols=100, desc='Загрузка фотографий на диск...'):
            self.upload_photos(folder_name, file_name, token)
        os.rmdir('profile photos')

# основная функция, с помощью которой запускаем код
    def main(self, owner_id, folder_name='VK PHOTOS'):
        self.create_folder(folder_name, YA_TOKEN)
        self.find_and_upload(owner_id, folder_name, YA_TOKEN)


access_token = VK_TOKEN
vk = VK(access_token)

#vk.main('нужный id')