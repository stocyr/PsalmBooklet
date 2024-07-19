import re

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


def all_after_verse_number(verse_element: Tag) -> [str, str]:
    vn_span = verse_element.find('span', class_='vn')
    # Extract all the text that comes after the 'vn' span
    text_after_vn = ''
    for element in vn_span.next_siblings:
        if isinstance(element, str):
            text_after_vn += element
        elif isinstance(element, Tag):
            text_after_vn += element.get_text()
    return text_after_vn.strip(), vn_span.get_text()


def grab_psalm(psalm_number) -> dict:
    # URL of the website to scrape
    url = f"https://bibel.github.io/EUe/ot/Ps_{psalm_number}.html"

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the element with class "biblehtmlcontent verses"
        content_div = soup.find('div', class_='biblehtmlcontent verses')

        if content_div:
            psalm_dict = {"number": psalm_number}
            # Find all elements with class "v" within the content_div
            verses = content_div.find_all('div', class_='v')

            # Extract the verses in their individual lines and their number
            psalm_dict["verses"] = {}
            search_for_verse_purpose = True
            for verse in verses:
                verse_text_raw, verse_number = all_after_verse_number(verse)
                # Preprocessing: Remove trailing [sela], "/" or footnote number
                for _ in range(3):
                    # Repeat multiple times because footnote or sela could occur together
                    verse_text_raw = re.sub(r"(/$)|(\d+$)|(\[Sela])|(\[Zwischenspiel. Sela])$", "",
                                            verse_text_raw).strip()
                # Replace break dashes (they have no character on either side)
                verse_text_raw = re.sub(r"(?<![a-zA-Z])-(?![a-zA-Z])", "–", verse_text_raw)
                verse_text = verse_text_raw
                # verse text can either:
                # 1. already contain the correct first sentence (e.g. 107)
                # 2. contain only the psalms purpose in [ ] brackets (e.g. 85)
                # 3. contain part of the psalms purpose, spread over multiple verses (e.g. 51)
                # 4. contain the psalms purpose and the correct first sentence (e.g. 86)
                if search_for_verse_purpose and verse_text.startswith("["):
                    # Psalms purpose starting
                    if verse_text.endswith("]"):
                        # Psalms purpose spreads the whole current verse -> skip
                        psalm_dict["purpose"] = verse_text.strip()
                        search_for_verse_purpose = False
                        continue
                    elif "]" not in verse_text:
                        # Psalms purpose spreads more than the current verse -> skip at least this one
                        psalm_dict["purpose"] = verse_text.strip()
                        continue
                    else:
                        # Psalms purpose spreads part of the current verse -> cut it out
                        psalm_dict["purpose"] = re.findall(r"\[.+?]", verse_text)[0].strip()
                        verse_text = re.sub(r"\[.+?]", "", verse_text).strip()
                        search_for_verse_purpose = False
                elif search_for_verse_purpose and "]" in verse_text:
                    if verse_text.endswith("]"):
                        # This verse ends completely with the psalms purpose -> skip it entirely
                        psalm_dict["purpose"] += " " + verse_text.strip()  # Multi-verse purpose: strip() removed space
                        search_for_verse_purpose = False
                        continue
                    else:
                        # Psalms purpose continued here since last verse -> only cut the first part
                        psalm_dict["purpose"] += " " + re.findall(r"^.+?]", verse_text)[0].strip()
                        verse_text = re.sub(r"^.+?]", "", verse_text).strip()
                        search_for_verse_purpose = False

                psalm_dict["verses"][verse_number] = [v.strip() for v in verse_text.split("/")]

            # At the last line of the last verse, append a Halleluja
            psalm_dict["verses"][verse_number][-1] += " – Halleluja!"
            return psalm_dict
        else:
            print("The specified class 'biblehtmlcontent verses' was not found.")
            raise ValueError()
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        raise ConnectionError()
