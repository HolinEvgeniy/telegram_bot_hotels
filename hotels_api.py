import requests
import json

from decouple import config
from typing import Union

headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': config('rapidapi_key')
}


def id_city(user_input: str) -> int:
    """
    Функция получения API по поиску города
    :param user_input: сообщение от пользователя о необходимом городе
    :return: id города, по которому производится поиск отелей
    """
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"

    querystring = {"query": user_input}

    response = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response.text)

    for i_group in data['suggestions']:
        if i_group['group'] == 'CITY_GROUP':
            if len(i_group['entities']) > 0:
                return i_group['entities'][0]['destinationId']
            else:
                return 0


def about_city(city_id: int) -> dict:
    """
    Функция получения информации по городу,
    в котором будет производится поиск с информацией об искомых отелях
    :param city_id: id города, в котором рассматриваем отели
    :return: данные о городе в формате list
    """
    url = "https://hotels4.p.rapidapi.com/properties/list"

    querystring = {"destinationId": city_id}

    response = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response.text)
    return data


def city_hotels(user_input: str) -> Union[int, list[dict]]:
    """
    Функция получения списка отелей в городе
    :param user_input: сообщение от пользователя о необходимом городе
    :return: список отелей в городе
    """
    if id_city(user_input) == 0:
        return 0
    else:
        hotels: list = about_city(id_city(user_input))['data']['body']['searchResults']['results']
        return hotels


def get_photos(hotel_id, amount_photo):
    """
    Функция получения фотографий с ресурса
    :param hotel_id: id отеля, фотографии которого запрашиваются
    :param amount_photo: количество фотографий для вывода
    """
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

    querystring = {"id": hotel_id}

    response = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response.text)
    need_list = [elem['baseUrl'].replace('{size}', 'z') for elem in data['hotelImages']]
    return need_list[:int(amount_photo)]
