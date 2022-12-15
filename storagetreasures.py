import json
import random
import string
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from requests.models import Response


class StorageTreasures:
    SITE_ROOT = "https://www.storagetreasures.com"
    API_ROOT = "https://api.st-prd-1.aws.storagetreasures.com/p"
    API_KEY = "oiXHdXqV7N1hm4y9qA8NGJCqBa9tSs6aU6dBBQCf"
    AUCTION_TYPES = {"current", "upcoming"}
    IMAGE_SIZES = {"thumb", "large", "giant"}
    FILTER_TYPE_LOOKUP = {
        "lien unit": "1",
        "non-lien unit/manager special": "2",
        "charity unit": "3",
    }
    CATEGORY_LOOKUP = {
        "appliances": "1",
        "arms": "12",
        "books": "2",
        "boxes": "3",
        "cabinets-and-shelves": "4",
        "clothing-and-shoes": "5",
        "collectibles": "6",
        "computers": "7",
        "dishes-and-kitchenware": "8",
        "documents-and-files": "9",
        "electronics": "10",
        "food-and-beverages": "11",
        "health-and-wellness": "13",
        "heavy-equipment": "14",
        "household-furniture": "15",
        "jewelry": "16",
        "lamps": "17",
        "mattress-and-bedding": "18",
        "memorabilia": "19",
        "mirrors": "20",
        "motor-vehicles-and-parts": "21",
        "movies-music-and-books": "22",
        "new-merchandise": "23",
        "office-equipment": "24",
        "old-stuff": "25",
        "personal-effects": "26",
        "sports-and-outdoors": "27",
        "tools-and-supplies": "28",
        "toys-baby-and-games": "29",
        "wall-art": "30",
    }

    def __init__(self):  # TODO possibly include a config and logger
        self.storage_treasures_session = requests.Session()
        self.storage_treasures_session.hooks[
            "response"
        ] = self.storage_treasures_err_hook

        # this is static on most (if not all?) pages on the site,
        # but we _could_ load it dynamically if we cared to
        self.storage_treasures_session.headers["x-api-key"] = StorageTreasures.API_KEY

    def storage_treasures_err_hook(self, res: Response, *args, **kwargs) -> None:
        """
        Simple error hook for the storage treasures requests client.
        This should catch all errors raised by JSON endpoints that still return
        with 2XX status codes

        :param res: A requests Response object
        :type res: Response
        :rtype: None
        """

        res.raise_for_status()

        if res.headers.get("content-type", "") == "application/json":
            api_response = res.json().get("status", "OK")
            if api_response != "OK":
                raise Exception("API JSON response returned with status {api_response}")

    def get_auction_info(self, auction_id: int) -> Dict:
        """
        Given a valid auction ID, return its relevant info.
        I couldn't find an API endpoint for this,
        so this function simply extracts the auction info JSON
        from a human-readable auction description webpage.

        :param auction_id: A valid auction ID
        :type auction_id: int
        :rtype: Dict
        """

        url = f"{StorageTreasures.SITE_ROOT}/auctions/detail/{auction_id}"
        res = self.storage_treasures_session.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        return json.loads(soup.find("script", {"id": "__NEXT_DATA__"}).text)

    def get_auction_image_urls(
        self, auction_id: int, image_size: Optional[str] = "large"
    ) -> List[str]:
        """
        Given a valid auction ID, return the URLs of all of its images
        in the desired image_size.

        :param auction_id: A valid auction ID
        :type auction_id: int
        :param image_size: The size of the images to return - defaults to "large"
            Other permissible values are in the IMAGE_SIZES constant
        :type image_size: Optional[str]
        :rtype: List[str]
        """

        if image_size not in StorageTreasures.IMAGE_SIZES:
            raise Exception(f"invalid image size {image_size}")

        auction_json = self.get_auction_info(auction_id)

        if image_size == "thumb":
            image_path_key = "image_path"
        else:
            image_path_key = f"image_path_{image_size}"

        return [
            image[image_path_key]
            for image in auction_json["props"]["initialState"]["auction"]["auction"][
                "images"
            ]
        ]

    def get_auctions(
        self,
        search_type: str,
        search_term: str,
        search_radius_miles: int,
        filter_types: Optional[List[str]] = None,
        filter_categories: Optional[List[str]] = None,
        unit_contents: Optional[str] = "",
        auction_type: Optional[str] = "current",
        page_count: Optional[int] = 30,
    ):
        """
        Given search parameters,
        return all auctions that match the specified criteria.
        This is a wrapper for the /auctions API endpoint.

        :param search_type:
        :type search_type: str
        :param search_term: The term to search,
            which should match the "search_type" value.
            eg. "90210" for search_type "zipcode"
        :type search_term: str
        :param search_radius_miles: The radius from the center(?) in miles
            of the search type / search term for which to display results
        :type search_radius_miles: int
        :param filter_types: An optional list of auction types to filter results.
            By default, this will include all entries in FILTER_TYPE_LOOKUP
        :type filter_types: Optional[List[str]]
        :param filter_categories: An optional list of categories to filter results.
            By default, this will include all entries in CATEGORY_LOOKUP
        :type filter_categories: Optional[List[str]]
        :param unit_contents: An optional description search value
        :type unit_contents: Optional[str]
        :param auction_type: If specified, either "upcoming" or "current".
            Defaults to "current"
        :type auction_type: Optional[str]
        :param page_count: The number of results to display per page.
            Defaults to 30 (as the webapp uses the same number)
        :type page_count: Optional[int]
        """
        if auction_type not in StorageTreasures.AUCTION_TYPES:
            raise Exception(f"invalid auction type {auction_type}")

        if filter_types is None:
            filter_types_str = ",".join(
                list(StorageTreasures.FILTER_TYPE_LOOKUP.values())
            )
        else:
            filter_types_str = ",".join(
                [StorageTreasures.FILTER_TYPE_LOOKUP[i] for i in filter_types]
            )

        if filter_categories is not None:
            filter_categories_str = ",".join(
                [StorageTreasures.CATEGORY_LOOKUP[i] for i in filter_categories]
            )
        else:
            filter_categories_str = ""

        params = {
            "page_num": 1,
            "page_count": page_count,
            "search_type": search_type,
            "search_term": search_term,
            "filter_types": filter_types_str,
            "filter_categories": filter_categories_str,
            "filter_unit_contents": unit_contents,
            "search_radius": search_radius_miles,
            "randStr": "".join(
                random.choice(string.ascii_lowercase + string.digits) for _ in range(10)
            ),  # looks akin to what the webapp does here
        }
        auctions = list()
        while True:
            res = self.storage_treasures_session.get(
                f"{StorageTreasures.API_ROOT}/auctions", params=params
            ).json()
            auctions.extend(res["auctions"])
            if len(auctions) >= int(res["total_records"]):
                break

        return auctions
