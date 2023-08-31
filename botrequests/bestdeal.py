from hotels_api import city_hotels
from typing import Union


def best_deal_sort_hotels(
        user_city: str,
        user_count_hotels: int,
        price_range: str,
        dist_range: str
) -> Union[int, list[dict]]:
    """
    Функция сортировки отелей по отдаленности от центра и
    по более дешевой цене с учетом введенных диапазонов пользователем
    :param user_city: запрашиваемый город пользователем
    :param price_range: диапазон цен
    :param dist_range: диапазон расстояния
    :param user_count_hotels: запрашиваемое количество отелей для вывода пользователем
    :return: список отелей по заданной сортировке
    """
    hotels_list = city_hotels(user_city)
    if hotels_list == 0:
        return 0
    else:
        list_price_range: list = price_range.split('-')
        list_dist_range: list = dist_range.split('-')
        need_list_price = filter(
            lambda elem:

            float(list_price_range[0]) <
            float(elem['ratePlan']['price']['exactCurrent']) <
            float(list_price_range[1]),

            hotels_list
        )
        need_list_dist = filter(
            lambda elem:

            float(list_dist_range[0]) <
            float(elem['landmarks'][0]['distance'].split()[0]) <
            float(list_dist_range[1]),

            need_list_price
        )
        result: list = list(need_list_dist)[:int(user_count_hotels)]
        if result == []:
            return 0
        else:
            return result
