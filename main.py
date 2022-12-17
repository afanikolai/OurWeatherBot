# Подключаем модуль случайных чисел 
import random
# Подключаем модуль для Телеграма
import telebot
# Указываем токен
#bot = telebot.TeleBot('5946859917:AAGtiScm-Cvo5AWGKZPQsxq_oqoZqE5Ndpg')
# Импортируем типы из модуля, чтобы создавать кнопки
from telebot import types

from aiogram import Bot, Dispatcher, executor, types

#from aiogram.types import inline_keyboard
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

#from typing import Literal
from urllib.request import urlopen

from dataclasses import dataclass
#import messages
from datetime import datetime
from enum import IntEnum
import json

from typing import Any

Celsius: Any = float

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

def weather() -> str:
    """Returns a message about the temperature and weather description"""
    wthr = get_weather(get_coordinates())
    return f'{wthr.location}, {wthr.description}\n' \
           f'Температура {wthr.temperature}°C, Ощущается как {wthr.temperature_feeling}°C \n' \
           f'{wthr.wind_direction} ветер {wthr.wind_speed} м/с \n'\
           f'Восход: {wthr.sunrise.strftime("%H:%M")}\n' \
           f'Закат: {wthr.sunset.strftime("%H:%M")}\n'

def start() -> str:
    """Returns a message about the temperature and weather description"""
    #wthr = get_weather(get_coordinates())
    return f'Привет этот бот говорит погоду по IP адресу или введенному слову\n' \
           f'Нажми нужную клавишу \n' \
           f'Введи /help для открытия српавки \n'\
           


#def wind() -> str:
#    """Returns a message about wind direction and speed"""
#    wthr = get_weather(get_coordinates())
#    return f'{wthr.wind_direction} wind {wthr.wind_speed} m/s'


#def sun_time() -> str:
#    """Returns a message about the time of sunrise and sunset"""
#    wthr = get_weather(get_coordinates())
#    return f'Sunrise: {wthr.sunrise.strftime("%H:%M")}\n' \
#           f'Sunset: {wthr.sunset.strftime("%H:%M")}\n'


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
    await message.answer(
        text=f'Прости я тебя не понял нажми /start чтобы начать диалог')

#@dp.message_handler(commands='wind')
#async def show_wind(message: types.Message):
#    await message.answer(text=messages.wind(), 
#                         reply_markup=WIND)


#@dp.message_handler(commands='sun_time')
#async def show_sun_time(message: types.Message):
#    await message.answer(text=messages.sun_time(), 
#                         reply_markup=SUN_TIME)


@dp.callback_query_handler(text='weather')
async def process_callback_weather(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        text=weather(),
        reply_markup=WEATHER
    )


#@dp.callback_query_handler(text='wind')
#async def process_callback_wind(callback_query: types.CallbackQuery):
#    await bot.answer_callback_query(callback_query.id)
#    await bot.send_message(
#        callback_query.from_user.id,
#        text=wind(),
#        reply_markup=WIND
#    )


#@dp.callback_query_handler(text='sun_time')
#async def process_callback_sun_time(callback_query: types.CallbackQuery):
#    await bot.answer_callback_query(callback_query.id)
#    await bot.send_message(
#        callback_query.from_user.id,
#        text=sun_time(),
#        reply_markup=SUN_TIME
#    )



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

BTN_WEATHER = InlineKeyboardButton('Прогноз погода по IP', callback_data='weather')
#BTN_WIND = InlineKeyboardButton('Прогноз погоды по введному городу', callback_data='wind')
#BTN_SUN_TIME = InlineKeyboardButton('Sunrise and sunset', callback_data='sun_time')

WEATHER = InlineKeyboardMarkup().add(BTN_WEATHER)
#WIND = InlineKeyboardMarkup().add(BTN_WEATHER,BTN_WIND)
#SUN_TIME = InlineKeyboardMarkup().add(BTN_WEATHER, BTN_WIND)
HELP = InlineKeyboardMarkup().add(BTN_WEATHER)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)