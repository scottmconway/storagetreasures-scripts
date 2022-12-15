#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import os
from collections import defaultdict

import storagetreasures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q", "--query-name", type=str, help="The name of the query to execute"
    )
    parser.add_argument(
        "--log-images",
        action="store_true",
        help="If set, log image hyperlinks in markdown format (useful for gotify)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="If set, execute all queries for the configured data source",
    )
    parser.add_argument(
        "-l",
        "--list-queries",
        action="store_true",
        help="If set, list all queries that can be executed "
        "for the current data source and exit",
    )
    args = parser.parse_args()

    with open("config.json", "r") as f:
        config = json.load(f)

    # logging setup
    logger = logging.getLogger("StorageTreasures_alert_on_new_query_results")
    logging_conf = config.get("logging", dict())
    logger.setLevel(logging_conf.get("log_level", logging.INFO))
    if "gotify" in logging_conf:
        from gotify_handler import GotifyHandler

        logger.addHandler(GotifyHandler(**logging_conf["gotify"]))

    stc = storagetreasures.StorageTreasures()
    saved_queries = config["saved_queries"]
    list_query_string = "Saved queries: %s" % (", ".join(saved_queries.keys()))

    if args.list_queries:
        print(list_query_string)
        return

    # init seen listings
    seen_listings_filename = config.get("seen_listings_filename", "seen_listings.json")
    if os.path.isfile(seen_listings_filename):
        with open(seen_listings_filename, "r") as f:
            seen_listings = json.load(f)

    else:
        seen_listings = dict()

    if not args.all and args.query_name not in saved_queries:
        logger.error(f'Invalid query_name "{args.query_name}" - exiting')
        exit(1)

    if args.all:
        queries_to_run = saved_queries
    else:
        queries_to_run = {args.query_name: saved_queries[args.query_name]}

    for query_name, query_json in queries_to_run.items():
        formatted_msg_lines = [""]
        query_res = stc.get_auctions(**query_json)

        alerts_by_location = defaultdict(lambda: list())

        for auction_info in query_res:
            # TODO possibly detect cancelled auctions, like this one
            # https://www.storagetreasures.com/auctions/detail/2598965
            # if auction_info['status_name'] == 'Canceled After Sold':
            #   TODO do something

            # skip seen listings
            auction_id = auction_info["auction_id"]
            if auction_id in seen_listings:
                continue

            facility_info = auction_info["facility"]
            relevant_attrs = {
                "auction_id": auction_id,
                "expire_time": datetime.datetime.fromisoformat(
                    auction_info["expire_date"]["utc"]["datetime"]
                ).isoformat(),
                "location": f"{facility_info['facility_name']} - {facility_info['city']}, {facility_info['state']}",
                "unit_number": auction_info["unit_number"],
                "unit_size": f"{auction_info['unit_width']} x {auction_info['unit_length']}",
                #'cleaning_deposit': f"{auction_info['']}",
                "sales_tax": f"{auction_info['sales_tax']}%",
                "cleanout_time": f"{auction_info['cleanout_time']} hours",
                "cleaning_deposit": auction_info["cleaning_deposit"]["formatted"],
                "url": f"https://www.storagetreasures.com/auctions/detail/{auction_id}",
            }

            # TODO can we fetch the premium from anywhere?
            # TODO investigate auction_info -> reserve_price

            seen_listings[auction_id] = relevant_attrs["expire_time"]
            alerts_by_location[facility_info["facility_id"]].append(relevant_attrs)
            formatted_msg_lines = [""]
            for facility_listings in alerts_by_location.values():
                formatted_msg_lines.append(f"{facility_listings[0]['location']}:  ")
                for listing in facility_listings:
                    alert_lines = [
                        f"[unit {listing['unit_number']} - {listing['unit_size']}]({listing['url']})  ",
                        listing[
                            "expire_time"
                        ],  # TODO this is in UTC - should we convert it back?
                        # TODO current bid?
                    ]

                    if args.log_images:
                        alert_lines.append(
                            " ".join(
                                [
                                    f"![]({img_url})"
                                    for img_url in stc.get_auction_image_urls(
                                        listing["auction_id"]
                                    )
                                ]
                            )
                        )
                    alert_lines.append("")
                    formatted_msg_lines.extend(alert_lines)
                formatted_msg_lines.append("")

        len_query_results = sum(
            [
                len(facility_auctions)
                for facility_auctions in alerts_by_location.values()
            ]
        )
        if len_query_results:
            formatted_msg_lines.insert(
                0,
                f'{len_query_results} new results for StorageTreasures query "{query_name}"  ',
            )
            logger.info("\n".join(formatted_msg_lines))

    # save new results of seen listings
    # but before we do, trim the stale entries
    now = datetime.datetime.utcnow()
    keys_to_drop = list()

    for item_id, end_time in seen_listings.items():
        if now > datetime.datetime.fromisoformat(end_time):
            keys_to_drop.append(item_id)

    for item_id in keys_to_drop:
        del seen_listings[item_id]

    with open(seen_listings_filename, "w") as f:
        json.dump(seen_listings, f)


if __name__ == "__main__":
    main()
