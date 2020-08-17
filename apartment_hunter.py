import requests
import bs4
import time

from bs4 import BeautifulSoup

# immoscout url:
# https://www.immobilienscout24.de/Suche/radius/wohnung-mieten?centerofsearchaddress={city};{ZIP-code};{street};;;{district}&numberofrooms={num-float-min}-{num-float-max}&price={num-float-min}-{num-float-max}&livingspace={num-float-min}-{num-float-max}&geocoordinates={long-float};{lat-float};{radius-float}
discord_url = "https://discordapp.com/api/webhooks/712762032713367553/edYMrRoM-5Ild-Ye5Lze2pCyu7NDB50iV3bwMpMksCua4SVHMoRpzMjh8k-SX1pIRQLU"
filter_params = ["Karlsruhe", "", "", "", 2, 4, 400, 700, 45, "", 49.008316, 8.402914, 6]


def parse(city: str, zip: str, street: str, district: str, room_num_min: float, room_num_max: float, price_min: float,
          price_max: float, living_space_min: float, living_space_max: float, long: float, lat: float, radius: float):
    """
    Parse all
    :param city:
    :param zip:
    :param street:
    :param district:
    :param room_num_min:
    :param room_num_max:
    :param price_min:
    :param price_max:
    :param living_space_min:
    :param living_space_max:
    :param long:
    :param lat:
    :param radius:

    :return:
    """
    url = "https://www.immobilienscout24.de/Suche/radius/wohnung-mieten?centerofsearchaddress={};{};{};;;{}&numberofrooms={}-{}&price={}-{}&livingspace={}-{}&geocoordinates={};{};{}".format(
        city, zip, street, district, room_num_min, room_num_max, price_min, price_max, living_space_min,
        living_space_max, long, lat, radius
    )
    print("parsing " + url)
    apartments = []
    page_num = 1

    html = htmlreader(url + "&pagenumber=" + str(page_num))
    parsed_apartments = parse_apartment(html)

    while len(parsed_apartments) != 0:
        page_num += 1
        apartments.extend(parsed_apartments)

        html = htmlreader(url + "&pagenumber=" + str(page_num))
        parsed_apartments = parse_apartment(html)

    apartments = {apartment["data-id"]: apartment for apartment in apartments}

    for id in apartments:
        apartments[id] = inspect_apartment(apartments.get(id))

    return apartments


def htmlreader(url: str):
    print(url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0',
        'Authority': 'www.immobilienscout24.de',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,de;q=0.8'
    }
    r = requests.get(url, headers=headers)
    print("request complete with status code", r.status_code)
    return r.text


def parse_apartment(html):
    soup = BeautifulSoup(html, "lxml")
    list_items = soup.find(id="resultListItems")
    if (not list_items):
        return []
    apartments = list_items.find_all("li", {"data-id": True}, recursive=False)
    return apartments


def inspect_apartment(apartment: bs4.Tag):
    price = None
    ls = None  # livingspace
    rooms = None
    title = None
    image = None
    url = None

    criteria = apartment.find_all(class_="result-list-entry__criteria")[0].find_all(
        class_="result-list-entry__primary-criterion")  # type:bs4.Tag
    price = criteria[0].find_all("dd")[0].text
    ls = criteria[1].find_all("dd")[0].text
    rooms = criteria[2].find_all("dd")[0].find_all(class_="onlySmall")[0].text
    title = apartment.find_all(class_="result-list-entry__brand-title")[0].find(text=True, recursive=False)

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
    request_payload = {
        "embeds": [
            {
                "title": "Ich lebe",
                "description": "Mein Leben ist cool, ich wurde nähhhhmlich gerade gestartet",
                "color": 5216170,
                "image": {
                    "url": "https://i.imgflip.com/1ocrfs.jpg"
                }
            }
        ]
    }
    response = requests.post(discord_url, json=request_payload)
    print("discord bot push response:", response.status_code)

    try:
        apartments = parse(*filter_params)
        while True:
            try:
                new_apartments = parse(*filter_params)
            except requests.exceptions.ConnectionError:
                continue

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
                    print("Sending new Apartment to discord")
                    print(response.text)
                    print(response.status_code)
                    time.sleep(5)

                apartments = new_apartments
            time.sleep(600)
    except:
        import traceback

        request_payload = {
            "embeds": [
                {
                    "title": "Ich bin abgestürzt, bitte helft mir",
                    "description": "Mein leben suckt, gib mir dick\n\n" + traceback.format_exc(),
                    "color": 16711680,
                    "image": {
                        "url": "https://banner2.cleanpng.com/20190624/tvh/kisspng-stop-sign-clip-art-image-traffic-sign-event-parking-allentown-parking-authority-5d10d437697042.0713188415613839914319.jpg"
                    }
                }
            ]
        }

        response = requests.post(discord_url, json=request_payload)
        print("Sending error message to discrod")
        print(response.status_code)
        raise
