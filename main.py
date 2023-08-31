import telebot
import random
import sqlite3
import datetime

from decouple import config
from telebot import types
from loguru import logger
from typing import Any

from botrequests import lowprice, history, highprice, bestdeal
from hotels_api import get_photos
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP


bot = telebot.TeleBot(config('token'))

conn = sqlite3.connect("history_database.db", check_same_thread=False)
cur = conn.cursor()

cur.execute(
            "CREATE TABLE IF NOT EXISTS story"
            "(user_id INTEGER, command TEXT, date_and_time TEXT, "
            "hotel_info TEXT, link_hotel TEXT)"
)

cur.execute(
        "CREATE TABLE IF NOT EXISTS inter_results"
        "(user_id INTEGER, start_date TEXT, stop_date TEXT)"
    )

conn.commit()


logger.add("logging.log", format="{time} {message}", level="DEBUG", rotation="1 day")


class MyStyleCalendar(DetailedTelegramCalendar):
    """
    Класс кастомизации календаря бота
    """
    prev_button = "⬅️"
    next_button = "➡️"
    empty_month_button = ""
    empty_year_button = ""
    empty_day_button = ""


def save_history_db(user_id, command, date_and_time, hotel_info, link_hotel) -> None:
    """
    Функция, заполняющая данными таблицу базы данных sqlite3
    :param user_id (int): id пользователя. Основной параметр для транслирования истории
    :param command (str): введенная команда от пользователя (метод бота)
    :param date_and_time (str): информация о выводе даты и времени необходимой команды
    :param hotel_info: информация о найденных ранее отелях
    """
    cur.execute(
        "INSERT INTO story (user_id, command, date_and_time, hotel_info, link_hotel)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, command, date_and_time, hotel_info, link_hotel)
    )
    conn.commit()


@bot.message_handler(commands=['start'])
def hello(message) -> None:
    """
    Функция вызова приветствия в чат с ботом
    :param message (message): всегда команда /start
    """
    greetings = {
        1: f'Привет, {message.from_user.first_name}!\nОчень рад тебя видеть!',
        2: f'Хай! Кто же ко мне пришел! {message.from_user.first_name}! Рад встрече!',
        3: f'Доброго времени суток, {message.from_user.first_name}!'
    }
    greetings_questions = {
        1: 'Хочешь узнать, что я умею?',
        2: 'Напомнить, что я умею?',
        3: 'Если не помните мои возможности, нажмите на кнопку "Да".'
    }
    choice = random.randint(1, 3)

    bot.send_message(message.chat.id, text=greetings[choice])
    keyboard = types.InlineKeyboardMarkup()
    help_button_yes = types.InlineKeyboardButton(text='Да', callback_data='helper')
    help_button_no = types.InlineKeyboardButton(text='Нет', callback_data='none')
    keyboard.add(help_button_yes, help_button_no)
    bot.send_message(message.chat.id, greetings_questions[choice], reply_markup=keyboard)
    logger.info(f"Пользователь {message.from_user.id} ввел {message.text} и запустил бота")


@bot.callback_query_handler(func=lambda call: call.data == 'helper' or call.data == 'none')
def callback_hello(call) -> None:
    """
    Функция обработки приветствия после нажатия кнопок в чате с ботом
    """
    if call.message:
        if call.data == 'none':
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Ну... в таком случае меня всегда можно вызвать с помощью /help')
        if call.data == 'helper':
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Прекрасно! Люблю помогать заинтересованным людям!')
            helper(call.message, call.from_user.id, call.data)


@bot.message_handler(commands=['help'])
def helper(message, user_id=None, user_message=None) -> Any:
    """
     Функция вызова возможных действий в чат с ботом
    :param message: всегда команда /help
    """
    help_commands = '/lowprice - покажу топ самых дешёвых отелей в городе\n' \
                    '/highprice - покажу топ самых дорогих отелей в городе\n' \
                    '/bestdeal - покажу топ отелей, наиболее подходящих по цене и расположению от центра\n' \
                    '/history - покажу историю поиска отелей'

    bot.send_message(message.chat.id, help_commands)

    command = r'Запущена команда: \help'
    date_and_time = f'Дата и время запроса: {datetime.datetime.today().date()}, ' \
                    f'{datetime.datetime.today().hour}:{datetime.datetime.today().minute}' \
                    f':{datetime.datetime.today().second}'
    hotel_info = None
    link = None

    save_history_db(
        user_id=user_id, command=command, date_and_time=date_and_time, hotel_info=hotel_info,
        link_hotel=link
    )
    action = None
    if user_message == 'helper':
        action = 'Да'
    elif user_message == 'none':
        action = 'Нет'
    logger.info(f"Пользователь {user_id} ввел {action} в функции {hello.__name__}")


@bot.message_handler(commands=['lowprice'])
def start_booking_low(message) -> None:
    """
    Функция вызова inline календаря для выбора даты начала бронирования отеля
    :param message: всегда команда /lowprice
    """
    bot.send_message(message.chat.id,
                     text=f'Для начала, {message.from_user.first_name}, '
                          f'давай определимся с датами бронирования отеля')
    calendar, step = MyStyleCalendar(min_date=datetime.datetime.today().date()).build()
    bot.send_message(message.chat.id, 'Выбери год начала бронирования', reply_markup=calendar)


@bot.callback_query_handler(func=MyStyleCalendar.func())
def call_start_booking_low(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    result, key, step = MyStyleCalendar(min_date=datetime.datetime.today().date()).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} начала бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        start_date = ''.join(str(result).split('-'))
        stop_date = None
        cur.execute(
            "INSERT INTO inter_results (user_id, start_date, stop_date)"
            " VALUES (?, ?, ?)",
            (user_id, start_date, stop_date)
        )
        conn.commit()
        bot.edit_message_text(f"Дата начала бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {call.from_user.id} ввел /lowprice в функции {helper.__name__}")
        end_booking_low(call.message, user_id)


def end_booking_low(message, user_id) -> None:
    """
    Функция вызова inline календаря для выбора даты окончания бронирования отеля
    :param message: результат нажатия inline кнопки календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == user_id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    calendar, step = MyStyleCalendar(
        calendar_id=1,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).build()
    bot.send_message(message.chat.id, f'Выбери год окончания бронирования', reply_markup=calendar)
    logger.info(f"Пользователь {user_id} выбрал дату начала бронирования {start_booking} "
                f"в функции {call_start_booking_low.__name__}")


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=1))
def call_stop_booking_low(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == call.from_user.id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    result, key, step = MyStyleCalendar(
        calendar_id=1,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} окончания бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        date = ''.join(str(result).split('-'))
        sql = f"""
            UPDATE inter_results 
            SET stop_date = {date}
            WHERE user_id = {user_id}
        """
        cur.execute(sql)
        conn.commit()
        bot.edit_message_text(f"Дата окончания бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {user_id} выбрал дату окончания бронирования {result} "
                    f"в функции {call_stop_booking_low.__name__}")
        low_price_hotels(call.message)


def low_price_hotels(message) -> None:
    """
    Функция обработки команды /lowprice.
    Вызов запроса искомого города
    :param message: всегда команда /lowprice
    """
    mes = bot.send_message(message.chat.id, text=f'Введи город на английском языке')
    bot.register_next_step_handler(mes, low_amount_hotels)


def low_amount_hotels(message) -> None:
    """
    Функция, которая запрашивает количество отелей, необходимых для вывода ботом
    :param message: передается ответ пользователя на запрос low_price_hotels
    """
    hotels_info = {}
    hotels_info['city'] = message.text
    count_hotels_mes = bot.send_message(message.chat.id,
                                        text=f"Рассматриваем город {hotels_info['city']}\nСколько отелей вывести?")
    logger.info(f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_price_hotels.__name__}")
    bot.register_next_step_handler(count_hotels_mes, low_photo, hotels_info)


def low_photo(message, hotels_info) -> None:
    """
    Функция запроса необходимости вывода фотографий от пользователя
    :param message: передается ответ пользователя на запрос low_amount_hotels
    :param hotels_info: передается словарь с информацией о предыдущих запросах lowprice
    """
    if message.text.isdigit():
        hotels_info['count_hotels'] = message.text
        need_photo = bot.send_message(message.chat.id, text='Нужно ли показать фотографии? (Да/Нет)')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_amount_hotels.__name__}"
        )
        bot.register_next_step_handler(need_photo, amount_low_photo, hotels_info)
    else:
        bot.send_message(message.chat.id, text='Я не понимаю... я ждал число!\nПопробуй снова /lowprice')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_amount_hotels.__name__}"
        )


def amount_low_photo(message, hotels_info) -> None:
    """
    Функция запроса количества выдаваемых фотографий ботом.
    Если на ресурсе фотографий меньше количества запрашиваемых,
    то бот отправляет то, количество, которое есть на ресурсе.
    :param message: передается ответ пользователя на запрос low_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах lowprice
    """
    if message.text.lower() == 'да':
        hotels_info['need_photo'] = message.text
        amount_photo = bot.send_message(message.chat.id,
                                        text='Сколько фотографий каждого отеля показать? (не более 10 штук)'
        )
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_photo.__name__}"
        )
        bot.register_next_step_handler(amount_photo, low_price_sort, hotels_info)
    elif message.text.lower() == 'нет':
        hotels_info['need_photo'] = message.text
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_photo.__name__}"
        )
        low_price_sort(message, hotels_info)
    else:
        bot.send_message(message.chat.id,
                         text=f'{message.from_user.first_name}, ожидал ответа "Да" или "Нет".\n'
                              f'Прошу повторить запрос /lowprice')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {low_photo.__name__}"
        )


def low_price_sort(message, hotels_info) -> None:
    """
    Основная функция вывода информации по всем предыдущим запросам метода бота lowprice
    :param message: передается ответ пользователя на запрос amount_low_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах lowprice
    """
    need_hotels = lowprice.low_price_sort_hotels(hotels_info['city'], hotels_info['count_hotels'])
    user_id = message.from_user.id
    if need_hotels == 0:
        bot.send_message(message.chat.id, text=f'{message.from_user.first_name}, скорей всего на ресурсе нет данных'
                                               f' по желаемому городу.\nПопробуйте снова ввести команду /lowprice')
    else:
        cur.execute('SELECT * FROM inter_results;')
        content = cur.fetchall()
        result = [i_story for i_story in content if i_story[0] == user_id]
        start_date = f'{result[0][1][:4]}-{result[0][1][4:6]}-{result[0][1][6:]}'
        end_date = f'{result[0][2][:4]}-{result[0][2][4:6]}-{result[0][2][6:]}'
        interval = int(
            (datetime.datetime.strptime(end_date, '%Y-%m-%d').date() -
             datetime.datetime.strptime(start_date, '%Y-%m-%d').date()).days
        )
        flag = False
        for i_hotel in need_hotels:
            name_hotel = i_hotel['name']
            address = f"{i_hotel['address']['postalCode']}, {i_hotel['address']['locality']}, " \
                      f"{i_hotel['address']['streetAddress']}"
            landmark = i_hotel['landmarks'][0]['distance']
            price = round(i_hotel['ratePlan']['price']['exactCurrent'] * interval, 2)
            hotel_id = i_hotel['id']
            link = f"Ссылка на отель: https://ru.hotels.com/ho{hotel_id}"

            if hotels_info['need_photo'].lower() == 'да':
                flag = True
                if message.text.isdigit():
                    hotels_info['count_photo'] = message.text
                    photo = get_photos(hotel_id, hotels_info['count_photo'])[:10]
                    text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                           f'Расстояние до центра города: {landmark}\n' \
                           f'Цена с учетом срока бронирования: ${price}\n{link}'
                    bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)
                    if int(hotels_info['count_photo']) > 10:
                        bot.send_message(message.chat.id,
                                         text=f'Запрошено количество фотографий больше максимального.'
                                              f'\nВывожу максимально допустимое количество фотографий.')
                    bot.send_media_group(message.chat.id,
                                         [types.InputMediaPhoto(i_photo)
                                          for i_photo in photo[:int(hotels_info['count_photo'])]])
                else:
                    bot.send_message(message.chat.id,
                                     text='Я не понимаю... я ждал число!\nПопробуй снова /lowprice')

            elif hotels_info['need_photo'].lower() == 'нет':
                hotels_info['count_photo'] = None
                text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                       f'Расстояние до центра города: {landmark}\n' \
                       f'Цена с учетом срока бронирования: ${price}\n{link}'
                bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)

            user_id = message.from_user.id
            command = r'Запущена команда: \lowprice'
            date_and_time = f'Дата и время запроса: {datetime.datetime.today().date()}, ' \
                            f'{datetime.datetime.today().hour}:{datetime.datetime.today().minute}' \
                            f':{datetime.datetime.today().second}'
            hotel_info = f'Название отеля: {name_hotel}\nАдрес отеля: {address}' \
                         f'\nРасстояние до центра: {landmark}\nЦена с учетом срока бронирования: ${price}'

            save_history_db(
                user_id=user_id, command=command, date_and_time=date_and_time,
                hotel_info=hotel_info, link_hotel=link
            )
        if flag:
            logger.info(
                f"Пользователь {message.from_user.id} ввел {message.text} в функции {amount_low_photo.__name__}"
            )
    sql = f"""
        DELETE FROM inter_results
        WHERE user_id = {user_id}
    """
    cur.execute(sql)
    conn.commit()
    logger.info(f"Бот вывел пользователю {user_id} запрашиваемую информацию")


@bot.message_handler(commands=['highprice'])
def start_booking_high(message) -> None:
    """
    Функция вызова inline календаря для выбора даты начала бронирования отеля
    :param message: всегда команда /highprice
    """
    bot.send_message(message.chat.id,
                     text=f'Для начала, {message.from_user.first_name}, '
                          f'давай определимся с датами бронирования отеля')
    calendar, step = MyStyleCalendar(calendar_id=2, min_date=datetime.datetime.today().date()).build()
    bot.send_message(message.chat.id, 'Выбери год начала бронирования', reply_markup=calendar)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=2))
def call_start_booking_high(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    result, key, step = MyStyleCalendar(calendar_id=2, min_date=datetime.datetime.today().date()).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} начала бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        start_date = ''.join(str(result).split('-'))
        stop_date = None
        cur.execute(
            "INSERT INTO inter_results (user_id, start_date, stop_date)"
            " VALUES (?, ?, ?)",
            (user_id, start_date, stop_date)
        )
        conn.commit()
        bot.edit_message_text(f"Дата начала бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {call.from_user.id} ввел /highprice в функции {helper.__name__}")
        end_booking_high(call.message, user_id)


def end_booking_high(message, user_id) -> None:
    """
    Функция вызова inline календаря для выбора даты окончания бронирования отеля
    :param message: результат нажатия inline кнопки календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == user_id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    calendar, step = MyStyleCalendar(
        calendar_id=3,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).build()
    bot.send_message(message.chat.id, 'Выбери год окончания бронирования', reply_markup=calendar)
    logger.info(f"Пользователь {user_id} выбрал дату начала бронирования {start_booking} "
                f"в функции {call_start_booking_high.__name__}")


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=3))
def call_stop_booking_high(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == call.from_user.id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    result, key, step = MyStyleCalendar(
        calendar_id=3,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} окончания бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        date = ''.join(str(result).split('-'))
        sql = f"""
            UPDATE inter_results 
            SET stop_date = {date}
            WHERE user_id = {user_id}
        """
        cur.execute(sql)
        conn.commit()
        bot.edit_message_text(f"Дата окончания бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {user_id} выбрал дату окончания бронирования {result} "
                    f"в функции {call_stop_booking_high.__name__}")
        high_price_hotels(call.message)


def high_price_hotels(message) -> None:
    """
    Функция обработки команды /highprice.
    Вызов запроса искомого города
    :param message: всегда команда /highprice
    """
    mes = bot.send_message(message.chat.id, text=f'Введите город на английском языке')
    bot.register_next_step_handler(mes, high_amount_hotels)


def high_amount_hotels(message) -> None:
    """
    Функция, которая запрашивает количество отелей, необходимых для вывода ботом
    :param message: передается ответ пользователя на запрос high_price_hotels
    """
    hotels_info = {}
    hotels_info['city'] = message.text
    count_hotels_mes = bot.send_message(message.chat.id,
                                    text=f"Рассматриваем город {hotels_info['city']}\nСколько отелей вывести?")
    logger.info(f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_price_hotels.__name__}")
    bot.register_next_step_handler(count_hotels_mes, high_photo, hotels_info)


def high_photo(message, hotels_info) -> None:
    """
    Функция запроса необходимости вывода фотографий от пользователя
    :param message: передается ответ пользователя на запрос high_amount_hotels
    :param hotels_info: передается словарь с информацией о предыдущих запросах highprice
    """
    if message.text.isdigit():
        hotels_info['count_hotels'] = message.text
        need_photo = bot.send_message(message.chat.id, text='Нужно ли показать фотографии? (Да/Нет)')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_amount_hotels.__name__}"
        )
        bot.register_next_step_handler(need_photo, amount_high_photo, hotels_info)
    else:
        bot.send_message(message.chat.id, text='Я не понимаю... я ждал число!\nПопробуй снова /highprice')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_amount_hotels.__name__}"
        )


def amount_high_photo(message, hotels_info) -> None:
    """
    Функция запроса количества выдаваемых фотографий ботом.
    Если на ресурсе фотографий меньше количества запрашиваемых,
    то бот отправляет то, количество, которое есть на ресурсе.
    :param message: передается ответ пользователя на запрос high_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах highprice
    """
    if message.text.lower() == 'да':
        hotels_info['need_photo'] = message.text
        amount_photo = bot.send_message(message.chat.id,
                                        text='Сколько фотографий каждого отеля показать? (не более 10 штук)'
        )
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_photo.__name__}"
        )
        bot.register_next_step_handler(amount_photo, high_price_sort, hotels_info)
    elif message.text.lower() == 'нет':
        hotels_info['need_photo'] = message.text
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_photo.__name__}"
        )
        low_price_sort(message, hotels_info)
    else:
        bot.send_message(message.chat.id,
                         text=f'{message.from_user.first_name}, ожидал ответа "Да" или "Нет".\n'
                              f'Прошу повторить запрос /lowprice')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {high_photo.__name__}"
        )


def high_price_sort(message, hotels_info) -> None:
    """
    Основная функция вывода информации по всем предыдущим запросам метода бота highprice
    :param message: передается ответ пользователя на запрос high_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах highprice
    """
    need_hotels = highprice.high_price_sort_hotels(hotels_info['city'], hotels_info['count_hotels'])
    user_id = message.from_user.id
    if need_hotels == 0:
        bot.send_message(message.chat.id, text=f'{message.from_user.first_name}, скорей всего на ресурсе нет данных'
                                               f' по желаемому городу.\nПопробуйте снова ввести команду /highprice')
    else:
        cur.execute('SELECT * FROM inter_results;')
        content = cur.fetchall()
        result = [i_story for i_story in content if i_story[0] == user_id]
        start_date = f'{result[0][1][:4]}-{result[0][1][4:6]}-{result[0][1][6:]}'
        end_date = f'{result[0][2][:4]}-{result[0][2][4:6]}-{result[0][2][6:]}'
        interval = int(
            (datetime.datetime.strptime(end_date, '%Y-%m-%d').date() -
             datetime.datetime.strptime(start_date, '%Y-%m-%d').date()).days
        )
        flag = False
        for i_hotel in need_hotels:
            name_hotel = i_hotel['name']
            address = f"{i_hotel['address']['postalCode']}, {i_hotel['address']['locality']}, " \
                      f"{i_hotel['address']['streetAddress']}"
            landmark = i_hotel['landmarks'][0]['distance']
            price = round(i_hotel['ratePlan']['price']['exactCurrent'] * interval, 2)
            hotel_id = i_hotel['id']
            link = f"Ссылка на отель: https://ru.hotels.com/ho{i_hotel['id']}"

            if hotels_info['need_photo'].lower() == 'да':
                flag = True
                if message.text.isdigit():
                    hotels_info['count_photo'] = message.text
                    photo = get_photos(hotel_id, hotels_info['count_photo'])[:10]
                    text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                           f'Расстояние до центра города: {landmark}\n' \
                           f'Цена с учетом срока бронирования: ${price}\n{link}'
                    bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)
                    if int(hotels_info['count_photo']) > 10:
                        bot.send_message(message.chat.id,
                                         text=f'Запрошено количество фотографий больше максимального.'
                                              f'\nВывожу максимально допустимое количество фотографий.')
                    bot.send_media_group(message.chat.id,
                                         [types.InputMediaPhoto(i_photo)
                                          for i_photo in photo[:int(hotels_info['count_photo'])]])
                else:
                    bot.send_message(message.chat.id,
                                     text='Я не понимаю... я ждал число!\nПопробуй снова /highprice')

            elif hotels_info['need_photo'].lower() == 'нет':
                hotels_info['count_photo'] = None
                text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                       f'Расстояние до центра города: {landmark}\n' \
                       f'Цена с учетом срока бронирования: ${price}\n{link}'
                bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)

            user_id = message.from_user.id
            command = r'Запущена команда: \highprice'
            date_and_time = f'Дата и время запроса: {datetime.datetime.today().date()}, ' \
                            f'{datetime.datetime.today().hour}:{datetime.datetime.today().minute}' \
                            f':{datetime.datetime.today().second}'
            hotel_info = f'Название отеля: {name_hotel}\nАдрес отеля: {address}' \
                         f'\nРасстояние до центра: {landmark}\n' \
                         f'Цена с учетом срока бронирования: ${price}'

            save_history_db(
                user_id=user_id, command=command, date_and_time=date_and_time,
                hotel_info=hotel_info, link_hotel=link
            )
        if flag:
            logger.info(
                f"Пользователь {message.from_user.id} ввел {message.text} в функции {amount_high_photo.__name__}"
            )
    sql = f"""
            DELETE FROM inter_results
            WHERE user_id = {user_id}
        """
    cur.execute(sql)
    conn.commit()
    logger.info(f"Бот вывел пользователю {user_id} запрашиваемую информацию")


@bot.message_handler(commands=['bestdeal'])
def start_booking_bestdeal(message) -> None:
    """
        Функция вызова inline календаря для выбора даты начала бронирования отеля
        :param message: всегда команда /bestdeal
        """
    bot.send_message(message.chat.id,
                     text=f'Для начала, {message.from_user.first_name}, '
                          f'давай определимся с датами бронирования отеля')
    calendar, step = MyStyleCalendar(calendar_id=4, min_date=datetime.datetime.today().date()).build()
    bot.send_message(message.chat.id, 'Выбери год начала бронирования', reply_markup=calendar)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=4))
def call_start_booking_bestdeal(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    result, key, step = MyStyleCalendar(calendar_id=4, min_date=datetime.datetime.today().date()).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} начала бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        start_date = ''.join(str(result).split('-'))
        stop_date = None
        cur.execute(
            "INSERT INTO inter_results (user_id, start_date, stop_date)"
            " VALUES (?, ?, ?)",
            (user_id, start_date, stop_date)
        )
        conn.commit()
        bot.edit_message_text(f"Дата начала бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {call.from_user.id} ввел /bestdeal в функции {helper.__name__}")
        end_booking_bestdeal(call.message, user_id)


def end_booking_bestdeal(message, user_id) -> None:
    """
    Функция вызова inline календаря для выбора даты окончания бронирования отеля
    :param message: результат нажатия inline кнопки календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == user_id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    calendar, step = MyStyleCalendar(
        calendar_id=5,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).build()
    bot.send_message(message.chat.id, 'Выбери год окончания бронирования', reply_markup=calendar)
    logger.info(f"Пользователь {user_id} выбрал дату начала бронирования {start_booking} "
                f"в функции {call_start_booking_bestdeal.__name__}")


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=5))
def call_stop_booking_bestdeal(call) -> None:
    """
    Обработчик нажатий inline кнопок календаря
    """
    cur.execute('SELECT * FROM inter_results;')
    content = cur.fetchall()
    result = [i_elem[1] for i_elem in content if i_elem[0] == call.from_user.id]
    start_booking = f'{result[0][:4]}-{result[0][4:6]}-{result[0][6:]}'
    result, key, step = MyStyleCalendar(
        calendar_id=5,
        min_date=datetime.datetime.strptime(start_booking, '%Y-%m-%d').date() + datetime.timedelta(days=1)
    ).process(call.data)
    if not result and key:
        if LSTEP[step] == 'month':
            bot_step = 'месяц'
        elif LSTEP[step] == 'day':
            bot_step = 'день'
        bot.edit_message_text(f"Выбери {bot_step} окончания бронирования",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        user_id = call.from_user.id
        date = ''.join(str(result).split('-'))
        sql = f"""
            UPDATE inter_results 
            SET stop_date = {date}
            WHERE user_id = {user_id}
        """
        cur.execute(sql)
        conn.commit()
        bot.edit_message_text(f"Дата окончания бронирования {result}",
                              call.message.chat.id,
                              call.message.message_id)
        logger.info(f"Пользователь {user_id} выбрал дату окончания бронирования {result} "
                    f"в функции {call_stop_booking_bestdeal.__name__}")
        best_deal_hotels(call.message)


def best_deal_hotels(message) -> None:
    """
    Функция обработки команды /bestdeal.
    Вызов запроса искомого города
    :param message: всегда команда /bestdeal
    """
    mes = bot.send_message(message.chat.id, text=f'Введите город на английском языке')
    bot.register_next_step_handler(mes, best_deal_price_range)


def best_deal_price_range(message) -> None:
    """
    Функция получения диапазона цен от пользователя
    :param message: передается ответ пользователя на запрос best_deal_hotels
    """
    hotels_info = {}
    hotels_info['city'] = message.text
    mes = bot.send_message(message.chat.id,
                           text='Введи диапазон интересующих цен в долларах в формате (число-число)')
    logger.info(f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_hotels.__name__}")
    bot.register_next_step_handler(mes, best_deal_dist_range, hotels_info)


def best_deal_dist_range(message, hotels_info) -> None:
    """
    Функция получения диапазона расстояния от пользователя
    :param message: передается ответ пользователя на запрос best_deal_price_range
    """
    hotels_info['price_range'] = message.text
    mes = bot.send_message(message.chat.id,
                           text='Введи диапазон интересующего расстояния до центра в милях в формате (число-число)')
    logger.info(
        f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_price_range.__name__}"
    )
    bot.register_next_step_handler(mes, best_deal_amount_hotels, hotels_info)


def best_deal_amount_hotels(message, hotels_info) -> None:
    """
    Функция, которая запрашивает количество отелей, необходимых для вывода ботом
    :param message: передается ответ пользователя на запрос best_deal_dist_range
    """
    hotels_info['dist_range'] = message.text
    count_hotels_mes = bot.send_message(message.chat.id,
                                        text=f"Рассматриваем город {hotels_info['city']}\nСколько отелей вывести?")
    logger.info(
        f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_dist_range.__name__}"
    )
    bot.register_next_step_handler(count_hotels_mes, best_deal_photo, hotels_info)


def best_deal_photo(message, hotels_info) -> None:
    """
    Функция запроса необходимости вывода фотографий от пользователя
    :param message: передается ответ пользователя на запрос best_deal_amount_hotels
    :param hotels_info: передается словарь с информацией о предыдущих запросах bestdeal
    """
    if message.text.isdigit():
        hotels_info['count_hotels'] = message.text
        need_photo = bot.send_message(message.chat.id, text='Нужно ли показать фотографии? (Да/Нет)')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_amount_hotels.__name__}"
        )
        bot.register_next_step_handler(need_photo, amount_bestdeal_photo, hotels_info)
    else:
        bot.send_message(message.chat.id, text='Я не понимаю... я ждал число!\nПопробуй снова /bestdeal')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_amount_hotels.__name__}"
        )


def amount_bestdeal_photo(message, hotels_info) -> None:
    """
    Функция запроса количества выдаваемых фотографий ботом.
    Если на ресурсе фотографий меньше количества запрашиваемых,
    то бот отправляет то, количество, которое есть на ресурсе.
    :param message: передается ответ пользователя на запрос best_deal_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах bestdeal
    """
    if message.text.lower() == 'да':
        hotels_info['need_photo'] = message.text
        amount_photo = bot.send_message(message.chat.id,
                                        text='Сколько фотографий каждого отеля показать? (не более 10 штук)'
        )
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_photo.__name__}"
        )
        bot.register_next_step_handler(amount_photo, best_deal_sort, hotels_info)
    elif message.text.lower() == 'нет':
        hotels_info['need_photo'] = message.text
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_photo.__name__}"
        )
        low_price_sort(message, hotels_info)
    else:
        bot.send_message(message.chat.id,
                         text=f'{message.from_user.first_name}, ожидал ответа "Да" или "Нет".\n'
                              f'Прошу повторить запрос /bestdeal')
        logger.info(
            f"Пользователь {message.from_user.id} ввел {message.text} в функции {best_deal_photo.__name__}"
        )


def best_deal_sort(message, hotels_info) -> None:
    """
    Основная функция вывода информации по всем предыдущим запросам метода бота bestdeal
    :param message: передается ответ пользователя на запрос best_deal_photo
    :param hotels_info: передается словарь с информацией о предыдущих запросах bestdeal
    """
    need_hotels = bestdeal.best_deal_sort_hotels(hotels_info['city'], hotels_info['count_hotels'],
                                                 hotels_info['price_range'], hotels_info['dist_range'])
    user_id = message.from_user.id
    if need_hotels == 0:
        bot.send_message(message.chat.id, text=f'{message.from_user.first_name}, скорей всего на ресурсе нет данных'
                                               f' по желаемому городу, или не найдено отеля с требуемыми данными.'
                                               f'\nПопробуй снова ввести команду /bestdeal')
    else:
        cur.execute('SELECT * FROM inter_results;')
        content = cur.fetchall()
        result = [elem for elem in content if elem[0] == user_id]
        start_date = f'{result[0][1][:4]}-{result[0][1][4:6]}-{result[0][1][6:]}'
        end_date = f'{result[0][2][:4]}-{result[0][2][4:6]}-{result[0][2][6:]}'
        interval = int(
            (datetime.datetime.strptime(end_date, '%Y-%m-%d').date() -
             datetime.datetime.strptime(start_date, '%Y-%m-%d').date()).days
        )
        flag = False
        for i_hotel in need_hotels:
            name_hotel = i_hotel['name']
            address = f"{i_hotel['address']['postalCode']}, {i_hotel['address']['locality']}, " \
                      f"{i_hotel['address']['streetAddress']}"
            landmark = i_hotel['landmarks'][0]['distance']
            price = round(i_hotel['ratePlan']['price']['exactCurrent'] * interval, 2)
            hotel_id = i_hotel['id']
            link = f"Ссылка на отель: https://ru.hotels.com/ho{i_hotel['id']}"

            if hotels_info['need_photo'].lower() == 'да':
                flag = True
                if message.text.isdigit():
                    hotels_info['count_photo'] = message.text
                    photo = get_photos(hotel_id, hotels_info['count_photo'])[:10]
                    text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                           f'Расстояние до центра города: {landmark}\n' \
                           f'Цена с учетом срока бронирования: ${price}\n{link}'
                    bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)
                    if int(hotels_info['count_photo']) > 10:
                        bot.send_message(message.chat.id,
                                         text=f'Запрошено количество фотографий больше максимального.'
                                              f'\nВывожу максимально допустимое количество фотографий.')
                    bot.send_media_group(message.chat.id,
                                         [types.InputMediaPhoto(i_photo)
                                          for i_photo in photo[:int(hotels_info['count_photo'])]])
                else:
                    bot.send_message(message.chat.id,
                                     text='Я не понимаю... я ждал число!\nПопробуй снова /bestdeal')

            elif hotels_info['need_photo'].lower() == 'нет':
                hotels_info['count_photo'] = None
                text = f'Название отеля: {name_hotel}\nАдрес: {address}\n' \
                       f'Расстояние до центра города: {landmark}\n' \
                       f'Цена с учетом срока бронирования: ${price}\n{link}'
                bot.send_message(message.chat.id, text=text, disable_web_page_preview=True)

            user_id = message.from_user.id
            command = r'Запущена команда: \bestdeal'
            date_and_time = f'Дата и время запроса: {datetime.datetime.today().date()}, ' \
                            f'{datetime.datetime.today().hour}:{datetime.datetime.today().minute}' \
                            f':{datetime.datetime.today().second}'
            hotel_info = f'Название отеля: {name_hotel}\nАдрес отеля: {address}' \
                         f'\nРасстояние до центра: {landmark}\n' \
                         f'Цена с учетом срока бронирования: ${price}'

            save_history_db(
                user_id=user_id, command=command, date_and_time=date_and_time,
                hotel_info=hotel_info, link_hotel=link
            )
        if flag:
            logger.info(
                f"Пользователь {message.from_user.id} ввел {message.text} "
                f"в функции {amount_bestdeal_photo.__name__}"
            )
    sql = f"""
                DELETE FROM inter_results
                WHERE user_id = {user_id}
            """
    cur.execute(sql)
    conn.commit()
    logger.info(f"Бот вывел пользователю {user_id} запрашиваемую информацию")


@bot.message_handler(commands=['history'])
def history_hotels_search(message) -> None:
    """
    Функция запроса вывода истории поиска отелей
    :param message: всегда команда /history
    """
    user_id = message.from_user.id
    search_list = history.history_search(conn, user_id)
    name = message.from_user.first_name
    if search_list == []:
        bot.send_message(message.chat.id, text=f'К сожалению, {name}, на данный момент история поиска пуста.')
    else:
        for i_elem in search_list:
            if i_elem[3] is None:
                bot.send_message(message.chat.id, text=f'{name}\n{i_elem[1]}\n{i_elem[2]}')
            else:
                bot.send_message(message.chat.id, text=f'{name}\n{i_elem[1]}\n{i_elem[2]}\n{i_elem[3]}'
                                                       f'\n{i_elem[4]}', disable_web_page_preview=True)
    logger.info(f"Пользователь {user_id} ввел /history в функции {helper.__name__}")
    logger.info(f"Бот вывел пользователю {user_id} запрашиваемую информацию")


if __name__ == '__main__':
    bot.infinity_polling()
