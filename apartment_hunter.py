from typing import List, Dict

import requests
import bs4
import time

from bs4 import BeautifulSoup

# immoscout url:
# https://www.immobilienscout24.de/Suche/radius/wohnung-mieten?centerofsearchaddress={city};{ZIP-code};{street};;;{district}&numberofrooms={num-float-min}-{num-float-max}&price={num-float-min}-{num-float-max}&livingspace={num-float-min}-{num-float-max}&geocoordinates={long-float};{lat-float};{radius-float}
discord_url = "https://discordapp.com/api/webhooks/712762032713367553/edYMrRoM-5Ild-Ye5Lze2pCyu7NDB50iV3bwMpMksCua4SVHMoRpzMjh8k-SX1pIRQLU"
immoscout_url = "https://www.immobilienscout24.de/Suche/radius/wohnung-mieten?centerofsearchaddress={};{};{};;;{}&numberofrooms={}-{}&price={}-{}&livingspace={}-{}&geocoordinates={};{};{}"
filter_params = ["Karlsruhe", "", "", "", 2, 4, 400, 800, 30, 90, 49.008316, 8.402914, 6]


def parse(city: str, zip_code: str, street: str, district: str, room_num_min: float, room_num_max: float,
          price_min: float,
          price_max: float, living_space_min: float, living_space_max: float, long: float, lat: float,
          radius: float) -> Dict:
    """
    Parse all apartments listed on immoscout according to the given filter params

    :param city: The city filter option
    :param zip_code: The zip code filter option
    :param street: The street filter option
    :param district: The district filter option
    :param room_num_min: The minimum room amount
    :param room_num_max: The max room amount
    :param price_min: The minimum price
    :param price_max: The maximum price
    :param living_space_min: The minimum living space
    :param living_space_max: The maximum living space
    :param long: Longitude coordinate
    :param lat: Latitude coordinate
    :param radius: search radius

    :return: The found apartments
    """
    url = immoscout_url.format(
        city, zip_code, street, district, room_num_min, room_num_max, price_min, price_max, living_space_min,
        living_space_max, long, lat, radius
    )
    print("parsing " + url)

    # parsing for each page until the page is empty
    apts = []
    page_num = 1

    html = html_reader(url + "&pagenumber=" + str(page_num))
    parsed_apartments = parse_apartment(html)

    while len(parsed_apartments) != 0:
        page_num += 1
        apts.extend(parsed_apartments)

        html = html_reader(url + "&pagenumber=" + str(page_num))
        parsed_apartments = parse_apartment(html)

    # convert list to dictionary
    apts = {apartment["data-id"]: apartment for apartment in apts}

    # parse room information
    for id in apts:
        apts[id] = inspect_apartment(apts.get(id))

    return apts


def html_reader(url: str) -> str:
    """
    Perform a http get request to a given url

    :param url: The url to request
    :return: The text of the response
    """
    r = requests.get(url)
    print("request complete with status code", r.status_code)
    return r.text


def parse_apartment(html: str) -> List[bs4.Tag]:
    """
    Parse all apartments of a html page

    :param html: The html page
    :return: The apartment list item tags as list
    """
    soup = BeautifulSoup(html, "lxml")
    return soup.find(id="resultListItems").find_all("li", {"data-id": True}, recursive=False)


def inspect_apartment(apartment: bs4.Tag) -> Dict:
    """
    Parse required information from a li tag of a apartment
    :param apartment: the li tag
    :return: the parsed information
    """
    criteria = apartment.find_all(class_="result-list-entry__criteria")[0].find_all(
        class_="result-list-entry__primary-criterion")  # type:bs4.Tag
    price = criteria[0].find_all("dd")[0].text
    ls = criteria[1].find_all("dd")[0].text
    rooms = criteria[2].find_all("dd")[0].find_all(class_="onlySmall")[0].text
    title = apartment.find_all(class_="result-list-entry__brand-title")[0].find(text=True, recursive=False)

    # as image urls may be in data-lazy-src or src this exception handling is required
    # also there might be no image at all
    try:
        image_tag = apartment.find_all(class_="result-list-entry__gallery-container")[0] \
            .find_all(class_="gallery__image")[0]
        try:
            image = image_tag["data-lazy-src"]
        except KeyError:
            image = image_tag["src"]
    except IndexError:
        image = "https://via.placeholder.com/180x180"

    url = "https://www.immobilienscout24.de/expose/" + apartment["data-id"]

    return {
        "price": price,
        "ls": ls,
        "rooms": rooms,
        "title": title,
        "image": image,
        "url": url
    }


if __name__ == '__main__':
    apartments = parse(*filter_params)
    while True:
        new_apartments = parse(*filter_params)

        if apartments.keys() != new_apartments.keys():
            new_keys = new_apartments.keys() - apartments.keys()
            for id in new_keys:
                # discord webhook
                request_payload = {
                    "embeds": [
                        {
                            "title": new_apartments.get(id)["title"],
                            "description": "**{}**\n**{}**\n**{}**".format(new_apartments.get(id)["price"],
                                                                           new_apartments.get(id)["rooms"],
                                                                           new_apartments.get(id)["ls"]),
                            "url": new_apartments.get(id)["url"],
                            "color": 7506394,
                            "image": {
                                "url": new_apartments.get(id)["image"]
                            }
                        }
                    ]
                }

                response = requests.post(discord_url, json=request_payload)
                print(response.text)
                print(response.status_code)
                time.sleep(5)

            apartments = new_apartments
        time.sleep(300)
