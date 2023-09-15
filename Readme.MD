# <center>**Hotel_analysis_bot**


![python](https://img.shields.io/pypi/pyversions/p?color=g&style=plastic)


![photo_hotel](https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQnaTucADaC8pKAWBedXE1hnReDwzQ8XFAuVYvmrkmpIee_5ixowJOZAWYIX0URgx9-1HI&usqp=CAU)

## **Описание**
____

Бот разработан на Python. Для реализации за основу была взята библиотека pytelegrambotapi, представляющая собой удобную и легкую библиотеку для создания ботов на Pyrhon для телеграма.
Бот выполняет 4 основные функции, а именно:

+ lowprice - подборка самых дешевых отелей города
+ highprice - подборка самых дорогих отелей города
+ bestdeal - подборка отелей, наиболее подходящих по цене и расположению от центра
+ history - вывод истории поиска отелей

![main_functions](images_for_readme/main_functions.jpg)

Результаты выполнения команд lowprice, highprice и bestdeal 
содержат краткую информацию по каждому отелю. 
В ответ входит:

+ название отеля
+ адрес
+ как далеко расположен от центра
+ цена за выбранный период времени бронирования
+ количество фотографий отеля (если пользователь сочтет необходимым их отобразить)

Для разработки проекта используется открытый API Hotels, находящийся на сайте Rapidapi.com.

```python
def id_city(user_input: str) -> int:
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
    url = "https://hotels4.p.rapidapi.com/properties/list"

    querystring = {"destinationId": city_id}

    response = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response.text)
    return data


def city_hotels(user_input: str) -> Union[int, list[dict]]:
    if id_city(user_input) == 0:
        return 0
    else:
        hotels: list = about_city(id_city(user_input))['data']['body']      ['searchResults']['results']
        return hotels
```

## **Основные функции**
____
### **lowprice**
После ввода команды пользователю будет предложено выбрать:
+ Город, в котором будут проводиться поиски.
+ Количество отелей, отображаемых в результате (не более
заданного максимума).
+ Необходимость загрузки и отображения фотографий по каждому отелю («Да/Нет»)
+ Если необходимо вывести фотографии, пользователь также вводит количество фотографий 
(не более заданного максимума, который ограничен самим Телеграмом)

![lowprice](images_for_readme/lowprice.jpg)

### **highprice**
После ввода команды пользователю будет предложено выбрать:
+ Город, в котором будут проводиться поиски.
+ Количество отелей, отображаемых в результате (не более
заданного максимума).
+ Необходимость загрузки и отображения фотографий по каждому отелю («Да/Нет»)
+ Если необходимо вывести фотографии, пользователь также вводит количество фотографий 
(не более заданного максимума, который ограничен самим Телеграмом)

![highprice](images_for_readme/highprice.jpg)

### **bestdeal**
После ввода команды пользователю будет предложено выбрать:
+ Город, в котором будут проводиться поиски.
+ Ценовой диапазон.
+ Удаленность расположения отеля от центра.
+ Количество отелей, отображаемых в результате (не более
заданного максимума).
+ Необходимость загрузки и отображения фотографий по каждому отелю («Да/Нет»)
+ Если необходимо вывести фотографии, пользователь также вводит количество фотографий 
(не более заданного максимума, который ограничен самим Телеграмом)

![bestdeal](images_for_readme/bestdeal.jpg)

Ко всем вышеперечисленным командам добавлена ​​функциональность календаря (бронирование отеля на определенные даты).

![calendar_year](images_for_readme/calendar_year.jpg)
![calendar_month](images_for_readme/calendar_month.jpg)
![calendar_day](images_for_readme/calendar_day.jpg)

Календарь реализован с помощью библиотеки telegram_bot_calendar.

```python
calendar, step = MyStyleCalendar(min_date=datetime.datetime.today().date()).build()

    def call_start_booking_low(call) -> None:
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
            bot.edit_message_text(f"Дата начала бронирования {result}",
                                  call.message.chat.id,
                                  call.message.message_id)

```

### **history**
После ввода команды пользователю отображается история поиска отелей. Сама история
содержит:
+ Команду, введенная пользователем.
+ Дату и время ввода команды.
+ Найденные отели с краткой информацией.

![history](images_for_readme/command_information.png)


## **Дополнительные функции**
____
### **help**
Вывод функциональности бота с его командами.

```python
    def helper(message, user_id, user_message) -> Any:
        help_commands = '/lowprice - покажу топ самых дешёвых отелей в  городе\n' \
                        '/highprice - покажу топ самых дорогих отелей в городе\n' \
                        '/bestdeal - покажу топ отелей, наиболее подходящих по цене и расположению от центра\n' \
                        '/history - покажу историю поиска отелей'

        bot.send_message(message.chat.id, help_commands)
```

![help](images_for_readme/help.jpg)

## **Старт**
____
Команда /start используется для запуска. После ввода команды отображается одно из трёх приветствий и предложение воспользоваться функцией помощи для напоминания существующих команд бота.

```python
    def hello(message) -> None:
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
```

![start](images_for_readme/start.jpg)
