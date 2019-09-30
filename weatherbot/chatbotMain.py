# Author: Jiacheng He
# Instructor: Fan Zhang
# Description: this is a simple chatbot which only can help you search weather
#              by city name, coordinate(in the form of latitude, longitude), and
#              US postal code. It offers languages and units choices which chould
#              show the description in other languages and convert units between
#              metric and imperial. Please check README to get more specific information.

import json
import time
import random
import spacy
import numpy as np
import requests
import pycountry as pc
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

# define my own telegram token and url with it
TOKEN = "949356860:AAG9yeUR4wG5LlyVyNIMwUFM-gKixyQfWVQ"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

nlp = spacy.load("en")
# Create a trainer that uses this config
trainer = Trainer(config.load("config_spacy.yml"))
# Load the training data
training_data = load_data('weather_rasa.json')
# Create an interpreter by training the model
interpreter = trainer.train(training_data)

INIT = 0
GET_WEATHER = 1
FINISH = 2
languages = ""
units = ""


# this function simply extract telegram url
def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


# this function retrieves a list of "updates" from telegram url
# if the offset is specified, it always does not receive any messages with smaller IDs than this
def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    content = get_url(url)
    js = json.loads(content)
    return js


# this function calculates the highest ID of all the updates
def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


# this function make sure that we always get the last input message to process
# and get the chat id to make sure that we are able to write feedback
def get_last_chat_id_and_text(updates):
    last_update = len(updates["result"]) - 1
    if last_update < 0:
        return None, None
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return text, chat_id


# this function sent message back which let the chatbot could speak to you
def send_message(message, chat_id):
    url = URL + "sendMessage?text={}&chat_id={}".format(message, chat_id)
    get_url(url)


# this function interpret the user input message and use the rasa-nlu package to extract intention
# and use both rasa-nlu and spacy package to extract name entities
# it will return the intent and entities list
def interpret(message):
    global nlp, interpreter
    data = interpreter.parse(message)
    intent = data["intent"]["name"]
    entities = data["entities"]
    if (intent == "greet" or intent == "start_searching" or intent == "affirm" or intent == "deny"
            or intent == "ask_else" or intent == "goodbye"):
        return intent, []
    elif intent == "ask_explanation":
        return intent, entities
    elif intent == "add_restriction":
        return intent, entities
    elif intent == "search_weather":
        doc = nlp(message)
        for ent in doc.ents:
            if ent.label_ == "GPE":
                ent_dic = {"value": ent.text, "entity": ent.label_}
                entities.append(ent_dic)
        return intent, entities
    return intent


# this function make the respond through policy_rules and responses
def respond(state, message, intent, entities, country_dic):
    responses = {
        "greet": ["Hi, I'm weatherbot, I could help you search current weather all around the world.",
                  "Hello, I'm a chatbot called weatherbot who could help you check weather at any place.",
                  "Hey, My name is weatherbot, I could help you check weathers around the world!"],
        "start_searching": ["Ok, let's start searching.\n{}", "Good, how do you want to search?\n{}",
                            "Great, where did you want to start searching.\n{}"],
        "affirm": ["Sounds great! what else do you want to do?", "Great, can I help you with anything else?",
                   "You are welcome, Is there anything else I can help with?"],
        "deny": ["Oops, something went wrong. {}",
                 "Sorry, I may not be able get correct weather data about this place. {}",
                 "I'm sorry, "],
        "ask_else": ["Ok, let's restart search.", "As you wish, let's start another search.",
                     "Ok, let's check another place.", "Clearing Data... let's search again"],
        "goodbye": ["Bye bye!", "See you next time.", "Goodbye, have a nice day!"]
    }
    explain_text = ""
    restrict_text = ""
    weather_text = ""
    if state == INIT and intent == "ask_explanation":
        explain_text = explanation(entities)
    elif state == INIT and intent == "add_restriction":
        restrict_text = restriction(entities)
    elif state == INIT and intent == "search_weather":
        location_list = get_location(message, entities, country_dic)
        weather_text = respond_weather(location_list)
    policy_rules = {
        (INIT, "greet"): (INIT, random.choice(responses["greet"])),
        (INIT, "ask_explanation"): (INIT, explain_text),
        (INIT, "add_restriction"): (INIT, restrict_text),
        (INIT, "start_searching"): (INIT, random.choice(responses["start_searching"])
                                    .format("You can search by city names, coordinates and US postal code.\n"
                                            "Hint: If you want to enter negative latitude or longitude, "
                                            "please separate negative sign from the number. Such as \"- 10\".")),
        (INIT, "search_weather"): (GET_WEATHER, weather_text),
        (GET_WEATHER, "affirm"): (FINISH, random.choice(responses["affirm"])),
        (GET_WEATHER, "deny"): (FINISH, random.choice(responses["deny"])
                                .format("You may restart search or exit the program.")),
        (FINISH, "ask_else"): (INIT, random.choice(responses["ask_else"])),
        (INIT, "goodbye"): (FINISH, random.choice(responses["goodbye"])),
        (GET_WEATHER, "goodbye"): (FINISH, random.choice(responses["goodbye"])),
        (FINISH, "goodbye"): (FINISH, random.choice(responses["goodbye"]))
    }

    new_state, response = policy_rules[(state, intent)]
    return new_state, response


# this function return an explanation about how to use the chatbot and how many setting options are there
def explanation(entities):
    if len(entities) == 0:
        return "You could set languages and units first or start searching directly.\n" \
               "If you have set already or just want to use default, please say start searching."
    for ent in entities:
        if ent["entity"] == "restriction":
            if ent["value"] == "languages":
                return "Unfortunately, I only offer the choice of Simplified Chinese and English.\n" \
                       "The default is English, no need to set again."
            elif ent["value"] == "units":
                return "Temperature is available in Fahrenheit, Celsius and Kelvin units.\n" \
                       "For temperature in Fahrenheit please set units as imperial.\n" \
                       "For temperature in Celsius please set units as metric\n" \
                       "Temperature in Kelvin is used by default, no need to set again."
    return ""


# this function will setup the language and unit for the system and give corresponding feedback
def restriction(entities):
    global languages, units
    if len(entities) == 0:
        return "No restriction added."
    for ent in entities:
        if ent["entity"] == "lang":
            languages = ent["value"]
            return "Set language as {} successfully!".format(ent["value"])
        if ent["entity"] == "unit":
            units = ent["value"]
            return "Set unit in {} successfully!".format(ent["value"])
    return ""


# this function will return a string which represent weather info with input location_list
def respond_weather(location_list):
    global languages, units
    result = "Getting the weather info...:\n"
    for location in location_list:
        weather_dic = {}
        if location["city"] != "":
            weather_dic = get_weather_info("", "", location["city"], "", languages, units)
        elif location["lat"] != "" and location["lon"] != "":
            weather_dic = get_weather_info(location["lat"], location["lon"], "", "", languages, units)
        elif location["postal"] != "":
            weather_dic = get_weather_info("", "", "", location["postal"], languages, units)
        if weather_dic["cod"] == 200:
            temp_unit = "°k"
            wind_unit = "m/s"
            if units == "metric":
                temp_unit = "°C"
            elif units == "imperial":
                temp_unit = "°F"
                wind_unit = "mph"
            result += "The weather of {}:\n".format(weather_dic["name"])
            result += "\t{}{}, {}\n".format(weather_dic["main"]["temp"], temp_unit,
                                            weather_dic["weather"][0]["description"])
            result += "\tClouds: {}%\n".format(weather_dic["clouds"]["all"])
            result += "\tHumidity: {}%\n".format(weather_dic["main"]["humidity"])
            result += "\tWind: {}{}\n".format(weather_dic["wind"]["speed"], wind_unit)
            result += "\tPressure: {}hpa\n".format(weather_dic["main"]["pressure"])
        else:
            result += "Oops, error message: {}\n".format(weather_dic["message"])
    return result


# this is a helper function which extract location info from the message into a list of locations
def get_location(message, entities, country_dic):
    location_list = []
    if len(entities) == 0:
        return location_list
    for ent in entities:
        location = ""
        lat = ""
        lon = ""
        postal = ""
        if ent["entity"] == "GPE":
            location = ent["value"]
            country = check_country_name(location, country_dic)
            if country != "":
                location = location + "," + country
        if ent["entity"] == "lat":
            lat = ent["value"]
            next_index = entities.index(ent) + 1
            lon = entities[next_index]["value"]
            index_lat = message.index(lat)
            index_lon = message.index(lon)
            if message[(index_lat-2): (index_lat-1)] == "-":
                lat = "-" + lat
            if message[(index_lon-2): (index_lon-1)] == "-":
                lon = "-" + lon
        if ent["entity"] == "lon":
            continue
        if ent["entity"] == "postal":
            # the api source only could check with US postal code
            postal = ent["value"] + ",us"
        location_info = {"city": location, "lat": lat, "lon": lon, "postal": postal}
        location_list.append(location_info)
    return location_list


# this is a helper function which check if the input GPE type location is a country name or not
def check_country_name(gpe_location, country_dic):
    for country in country_dic.values():
        if (country["alpha2"] == gpe_location or country["alpha3"] == gpe_location
                or country["name"] == gpe_location or country["official_name"] == gpe_location
                or country["common_name"] == gpe_location):
            return country["alpha2"]
    return ""


# this function build a dictionary of countries by the pycountry package
def build_country_dic():
    country_list = list(pc.countries)
    country_dic = {}
    for country in country_list:
        if country.name not in country_dic.keys():
            country_dic[country.name] = {"alpha2": country.alpha_2, "alpha3": country.alpha_3,
                                         "name": country.name, "official_name": "", "common_name": ""}
        if hasattr(country, "official_name"):
            country_dic[country.name]["official_name"] = country.official_name
        if hasattr(country, "common_name"):
            country_dic[country.name]["common_name"] = country.common_name
    return country_dic


# this function get api link with my api key and set up the url properly to extract the weather info in json format
def get_weather_info(lat, lon, location, postal, lang, unit):
    api_key = "8f418eec31daa053b149f4363269e47d"
    url = "https://api.openweathermap.org/data/2.5/weather?appid={}".format(api_key)
    if location != "":
        url += "&q={}".format(location)
    if lat != "" and lon != "":
        url += "&lat={}&lon={}".format(lat, lon)
    if postal != "":
        url += "&zip={}".format(postal)
    if lang != "":
        url += "&lang={}".format(lang)
    if unit != "":
        url += "&units={}".format(unit)
    response = requests.request("GET", url)
    return response.json()


def main():
    last_update_id = None
    country_dic = build_country_dic()
    state = INIT
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            message, chat_id = get_last_chat_id_and_text(updates)
            intent, entities = interpret(message)
            state, message = respond(state, message, intent, entities, country_dic)
            send_message(message, chat_id)
            if state == FINISH and intent == "goodbye":
                send_message("Program exit.\nIf you want to search the weather, please restart the program!", chat_id)
                break
        time.sleep(.5)


if __name__ == '__main__':
    main()
