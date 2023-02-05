import datetime
import io
import json
import logging
import os
import re
import sys

import pandas as pd
import requests
from twilio.rest import Client


def twilio_client_setup():
    twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

    return twilio_client


def set_quantity_requirement():
    while True:
        try:
            if len(sys.argv) > 1:
                quantity = sys.argv[1]
            else:
                quantity = input("How many tickets would you like?")
            quantity_int = int(quantity)
            break
        except ValueError:
            logging.error("\nPlease enter an integer (eg. 3)")
    return quantity_int


def set_price_requirement():
    while True:
        try:
            if len(sys.argv) > 1:
                max_price = sys.argv[2]
            else:
                max_price = input("What is the maximum price (in USD) that you will pay?")
            max_price_clean = re.search("[\d,.]+", max_price).group(0)
            max_price_clean = re.sub(",", "", max_price_clean)

            max_price_float = float(max_price_clean)
            break

        except ValueError:
            logging.error("\nPlease enter an valid number (eg. 125, 250.75) ")

    return max_price_float


def set_request_frequency():
    while True:
        try:
            if len(sys.argv) > 1:
                frequency = sys.argv[3]
            else:
                frequency = input("How often should I check for new tickets (in minutes)? ")
            frequency_int = int(frequency) * 60
            break
        except ValueError:
            logging.error("\nPlease enter an valid integer (eg. 30, 50, 18) ")

    return frequency_int


class TickPickRequest:
    def __init__(self, event_id):
        self.event_id = event_id
        self.event_name = ""
        self.event_info = ""
        self.event_date = ""

        self.quantity = set_quantity_requirement()
        self.max_price = set_price_requirement()
        self.frequency = set_request_frequency()

        self.count_available_tickets = 0

        with open("data/seen_tickets.json") as json_file:
            json_decoded = json.load(json_file)

        try:
            self.texts_sent = set(json_decoded[f'{self.event_id}_{self.quantity}_{self.max_price}'])
        except KeyError:
            self.texts_sent = set()
        except json.decoder.JSONDecodeError:
            self.texts_sent = set()

    def get_event_details(self):
        event_info = requests.get(f"https://api.tickpick.com/1.0/events/{self.event_id}")
        event_info_json = event_info.json()
        self.event_name = event_info_json['display_name']
        self.event_info = event_info_json['description']
        self.event_date = re.search("\d{4}-\d{2}-\d{2}", event_info_json['event_date']).group(0)

        print(f"---\n\nSetting Event:\n {self.event_name} - {self.event_info} on {self.event_date}\n")

    def check_inventory(self):
        tick_pick_listing_url = "https://api.tickpick.com/1.0/listings/internal/event/"

        ticket_info = requests.get(f"{tick_pick_listing_url}{self.event_id}").content
        ticket_df = pd.read_json(io.StringIO(ticket_info.decode('utf-8')), orient='columns')

        ticket_df_quantity = ticket_df[(ticket_df["q"] >= self.quantity) & (ticket_df["p"] <= self.max_price)]
        no_parking = ticket_df_quantity[~ticket_df_quantity["n"].apply(str.lower).str.contains("park")]

        print("CURRENT TICKETS: ", no_parking.shape[0], "tickets as of", datetime.datetime.now())

        if no_parking.shape[0] > 0:
            ids = list(no_parking['id'])
            self.count_available_tickets = no_parking.shape[0]
        else:
            ids = None
        return no_parking.shape[0], ids

    def update_cache(self):
        with open("data/seen_tickets.json", "r") as json_file:
            json_decoded = json.load(json_file)
            json_decoded[f'{self.event_id}_{self.quantity}_{self.max_price}'] = list(self.texts_sent)

        with open("data/seen_tickets.json", 'w') as json_file:
            json.dump(json_decoded, json_file)

    def send_text(self, ticket_list):
        for tick in ticket_list:
            if tick not in self.texts_sent:
                logging.info(f"Sending text to {os.getenv('YOUR_PHONE_NUMBER')}")
                twilio_client_setup().messages \
                    .create(
                    body=f"There are {self.count_available_tickets} tickets available under ${self.max_price} for"
                         f" {self.event_info} on {self.event_date}! \nhttps://www.tickpick.com/buy-tickets/{self.event_id}",
                    from_=os.getenv("TWILIO_PHONE_NUMBER"),
                    to=os.getenv('YOUR_PHONE_NUMBER')
                )
                for x in ticket_list:
                    self.texts_sent.add(x)
                break  # only send one text message. no need to send multiple
        self.update_cache()
