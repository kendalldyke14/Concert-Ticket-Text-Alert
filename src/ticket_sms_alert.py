import json
import os
import time
from dotenv import load_dotenv
import logging

import TickPickRequest


def create_cache_file():
    if not os.path.exists("data/seen_tickets.json"):
        try:
            os.makedirs("data/")
        except FileExistsError:
            pass
        with open("data/seen_tickets.json", "w") as json_new:
            json.dump({}, json_new)


if __name__ == '__main__':
    load_dotenv()
    create_cache_file()

    tick_pick_request_info = TickPickRequest.TickPickRequest(os.getenv("EVENT_ID"))
    tick_pick_request_info.get_event_details()

    while True:
        num_tickets, ticket_id_list = tick_pick_request_info.check_inventory()

        logging.info("Quantity:", num_tickets, " - Ticket Id(s)", ticket_id_list)

        if (num_tickets > 0) & (ticket_id_list is not None):
            tick_pick_request_info.send_text(ticket_id_list)

        time.sleep(tick_pick_request_info.frequency)
