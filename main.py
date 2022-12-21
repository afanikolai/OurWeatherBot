import telebot, json, os
from telebot import types
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from urllib.request import urlopen
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any
from time import sleep, perf_counter
from threading import Thread, Event
import pandas as pd

Celsius: Any = float
city_db = pd.read_csv('city.csv')
subscribers = {}
save_delay = 10

from weatherAPI_token import WEATHER_API_KEY 
from telegram_token import BOT_API_TOKEN 

CURRENT_WEATHER_API_CALL = (
        'https://api.openweathermap.org/data/2.5/weather?'
        'lat={latitude}&lon={longitude}&'
        'appid=' + WEATHER_API_KEY + '&units=metric'
)

@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

def get_coordinates() -> Coordinates:
    """Returns current coordinates using IP address"""
    data = _get_ip_data()
    latitude = data['loc'].split(',')[0]
    longitude = data['loc'].split(',')[1]

    return Coordinates(latitude=latitude, longitude=longitude)

def _get_ip_data() -> dict:
    url = 'http://ipinfo.io/json'
    response = urlopen(url)
    return json.load(response)

def weather(coordinates) -> str:
    """Returns a message about the temperature and weather description"""
    wthr = get_weather(coordinates)
    return f'{wthr.location}, {wthr.description}\n' \
           f'Температура {wthr.temperature}°C, Ощущается как {wthr.temperature_feeling}°C \n' \
           f'{wthr.wind_direction} ветер {wthr.wind_speed} м/с \n'\
           f'Восход: {wthr.sunrise.strftime("%H:%M")}\n' \
           f'Закат: {wthr.sunset.strftime("%H:%M")}\n'

def start() -> str:
    """Returns a message about the temperature and weather description"""
    return f'Привет этот бот говорит погоду по IP адресу или введенному слову\n' \
           f'Нажми нужную клавишу \n' \
           f'Введи /help для открытия справки \n'\
           
bot = Bot(token=BOT_API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'weather'])
async def show_weather(message: types.Message):
    await message.answer(text=start(),
                         reply_markup=WEATHER)

@dp.message_handler(commands='help')
async def show_help_message(message: types.Message):
    await message.answer(
        text=f'Привет этот бот говорит погоду по IP адресу или введенному слову',
        reply_markup=HELP)

@dp.message_handler(content_types=["text"])
async def warnings(message: types.Message):
    mask_city = city_db['city'].str.lower() == message.text.lower()
    mask_region = city_db['region'].str.lower() == message.text.lower()
    found_data = pd.concat([pd.DataFrame(city_db[mask_city]), pd.DataFrame(city_db[mask_region])], ignore_index=True)
    if found_data.shape[0] > 0:
        await message.answer(
        text=weather(Coordinates(latitude=str(found_data.iloc[0]['geo_lat']), longitude=str(found_data.iloc[0]['geo_lon']))),
        reply_markup=WEATHER)
    else:
        await message.answer(
        text='Такого города нет в моем списке, попробуй еще раз',
        reply_markup=None)

@dp.callback_query_handler(text='weather')
async def process_callback_weather(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        text=weather(get_coordinates()),
        reply_markup=WEATHER
    )

@dp.callback_query_handler(text='city_weather')
async def process_callback_city_weather(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        'Введи название города без сокращений'
    )

@dp.callback_query_handler(text='subscribe')
async def process_callback_download_weather_history(callback_query: types.CallbackQuery):
    if not subscribers.keys().__contains__(callback_query.from_user.id):
        # Добавляем пользователя и его координаты в список подписчиков
        subscribers[callback_query.from_user.id] = get_coordinates()
        await bot.send_message(
        callback_query.from_user.id,
        'Теперь я буду сохранять историю погоды в вашем городе, вы можете скачать ее в любой момент')
    else: 
        await bot.send_message(callback_query.from_user.id,
        'Вы уже подписаны на сохранение истории погоды')

@dp.callback_query_handler(text='unsubscribe')
async def process_callback_download_weather_history(callback_query: types.CallbackQuery):
    if subscribers.keys().__contains__(callback_query.from_user.id):
        del subscribers[callback_query.from_user.id]
        cols = ["user_id", "lat", "lon", "timestamp", "weather"]
        df = pd.read_csv('saved.csv', usecols=cols)
        df.drop(df[df['user_id'] == callback_query.from_user.id].index, inplace = True)
        df.to_csv('saved.csv')
        await bot.send_message(
        callback_query.from_user.id,
        'Больше не буду сохранять погоду для вас')
    else: 
        await bot.send_message(callback_query.from_user.id,
        'Вы не подписаны на сохранение истории погоды')

@dp.callback_query_handler(text='download_weather_history')
async def process_callback_download_weather_history(callback_query: types.CallbackQuery):
    cols = ["user_id", "lat", "lon", "timestamp", "weather"]
    df = pd.read_csv('saved.csv', usecols=cols)
    mask = df['user_id'] == callback_query.from_user.id
    df = pd.DataFrame(df[mask])
    if not df.empty:
        df.to_csv('Weather_history.csv')
        await bot.send_document(chat_id=callback_query.from_user.id, document=open('Weather_history.csv', 'rb'))
        os.remove("Weather_history.csv")
    else: 
        await bot.send_message(callback_query.from_user.id,
        'Вы не подписаны на сохранение истории погоды, подпишитесь :)')

def save_weather(user_id, coordinates):
    cols = ["user_id", "lat", "lon", "timestamp", "weather"]
    db = pd.read_csv('saved.csv', usecols=cols)
    new_row = pd.DataFrame({
        'user_id': [user_id], 
        'lat':[coordinates.latitude], 
        'lon':[coordinates.longitude], 
        'timestamp': [datetime.now()], 
        'weather': [get_weather(coordinates)]})
    db.reset_index(drop=True, inplace=True)
    new_row.reset_index(drop=True, inplace=True)
    db = pd.concat([db, new_row], ignore_index=True)
    print(db)
    db.to_csv('saved.csv')

class WindDirection(IntEnum):
    North = 0
    Northeast = 45
    East = 90
    Southeast = 135
    South = 180
    Southwest = 225
    West = 270
    Northwest = 315

@dataclass(frozen=True)
class Weather:
    location: str
    temperature: Celsius #было в цельсиях см начало
    temperature_feeling: Celsius #было в цельсиях см начало
    description: str
    wind_speed: float
    wind_direction: str
    sunrise: datetime
    sunset: datetime

def get_weather(coordinates=Coordinates) -> Weather:
    """Requests the weather in OpenWeather API and returns it"""
    openweather_response = _get_openweather_response(
        longitude=coordinates.longitude, latitude=coordinates.latitude
    )
    weather = _parse_openweather_response(openweather_response)
    return weather

def _get_openweather_response(latitude: float, longitude: float) -> str:
    url = CURRENT_WEATHER_API_CALL.format(latitude=latitude, longitude=longitude)
    return urlopen(url).read()

def _parse_openweather_response(openweather_response: str) -> Weather:
    openweather_dict = json.loads(openweather_response)
    return Weather(
        location=_parse_location(openweather_dict),
        temperature=_parse_temperature(openweather_dict),
        temperature_feeling=_parse_temperature_feeling(openweather_dict),
        description=_parse_description(openweather_dict),
        sunrise=_parse_sun_time_sunrise(openweather_dict),
        sunset=_parse_sun_time_sunset(openweather_dict),
        wind_speed=_parse_wind_speed(openweather_dict),
        wind_direction=_parse_wind_direction(openweather_dict)
    )

def _parse_location(openweather_dict: dict) -> str:
    return openweather_dict['name']

def _parse_temperature(openweather_dict: dict) -> Celsius:
    return openweather_dict['main']['temp']

def _parse_temperature_feeling(openweather_dict: dict) -> Celsius:
    return openweather_dict['main']['feels_like']

def _parse_description(openweather_dict) -> str:
    return str(openweather_dict['weather'][0]['description']).capitalize()

def _parse_sun_time_sunrise(openweather_dict: dict) -> datetime:
    return datetime.fromtimestamp(openweather_dict['sys']['sunrise']) 

def _parse_sun_time_sunset(openweather_dict: dict) -> datetime: 
    return datetime.fromtimestamp(openweather_dict['sys']['sunset'])

def _parse_wind_speed(openweather_dict: dict) -> float:
    return openweather_dict['wind']['speed']

def _parse_wind_direction(openweather_dict: dict) -> str:
    degrees = openweather_dict['wind']['deg']
    degrees = round(degrees / 45) * 45
    if degrees == 360:
        degrees = 0
    return WindDirection(degrees).name

BTN_WEATHER = InlineKeyboardButton('Прогноз погоды по IP', callback_data='weather')
BTN_CITY_WEATHER = InlineKeyboardButton('Прогноз погоды по введному городу', callback_data='city_weather')
BTN_SUBSCRIBE_FOR_HISTORY = InlineKeyboardButton('Подписаться на сохранение данных о погоде', callback_data='subscribe')
BTN_UNSUBSCRIBE_FROM_HISTORY = InlineKeyboardButton('Отписаться от сохранения данных', callback_data='unsubscribe')
BTN_DOWNLOAD_WEATHER_HISTORY = InlineKeyboardButton('Скачать историю погоды', callback_data='download_weather_history')

WEATHER = InlineKeyboardMarkup().add(BTN_WEATHER).add(BTN_CITY_WEATHER).add(BTN_SUBSCRIBE_FOR_HISTORY).add(BTN_DOWNLOAD_WEATHER_HISTORY).add(BTN_UNSUBSCRIBE_FROM_HISTORY)
HELP = InlineKeyboardMarkup().add(BTN_WEATHER)

def get_subscribers():
    cols = ["user_id", "lat", "lon", "timestamp", "weather"]
    df = pd.read_csv('saved.csv', usecols=cols)
    df = df.drop_duplicates('user_id')
    arr = df.to_numpy()
    for item in arr:
        subscribers[item[0]] = Coordinates(item[1], item[2])

def saver():
    while True:
        for user_id in subscribers:
            save_weather(user_id, subscribers[user_id])
        sleep(save_delay)
        if event.is_set():
            break

event = Event()
my_thread = Thread(target=saver)

def stop_thread(props):
    event.set()
    my_thread.join()

if __name__ == '__main__':
    get_subscribers()
    my_thread.start()
    executor.start_polling(dp, skip_updates=True, on_shutdown=stop_thread)
    