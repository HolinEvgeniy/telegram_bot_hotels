from hotels_api import city_hotels
from typing import Union


def low_price_sort_hotels(user_city: str, user_count_hotels: int) -> Union[int, list[dict]]:
    """
    Функция вывода отсортированных отелей от самого дешевого до самого дорогого
    :param user_city: запрашиваемый город пользователем
    :param user_count_hotels: запрашиваемое количество отелей для вывода пользователем
    :return: список отелей по заданной сортировке
    """
    hotels_list = city_hotels(user_city)
    if hotels_list == 0:
        return 0
    else:
        sort_hotels_list: list = sorted(hotels_list, key=lambda elem: elem['ratePlan']['price']['exactCurrent'])
        need_list_hotels: list = sort_hotels_list[:int(user_count_hotels)]
        return need_list_hotels
