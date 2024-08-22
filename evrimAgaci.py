import base64
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import json
import os
from dotenv import load_dotenv

load_dotenv()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
API_URL = os.getenv('API_URL')
def process_image(image_url:str):

    banner_response = requests.get(image_url)
    banner_base64 = base64.b64encode(banner_response.content).decode('utf-8')
    payload = {
        "file": f"data:image/png;base64,{banner_base64}",
        "is_listing_attachment": False
    }
    attachment_response = requests.post(API_URL, json=payload, headers=HEADERS)
    attachment_response.raise_for_status()
    new_url = attachment_response.json()
    return new_url

def parse(article_url: str):
    response = requests.get(article_url)
    soup = BeautifulSoup(response.content, "html.parser")

    content_container = soup.select_one(".content-container")

    title_element = content_container.select_one(".header>.title")
    title_element.attrs = {}
    title_html = str(title_element) if title_element else "Başlıksız"
    
    banner_url = content_container.select_one(".header>figure").attrs.get("data-src")
    new_banner_url = process_image(banner_url)

    content_element = content_container.select_one("#content")

    figure_elements = content_element.select(".figure-image")
    image_urls = []
    for figure_element in figure_elements:
        figure_url = figure_element.attrs.get("data-src")
        new_url = process_image(figure_url)
        image_urls.append(new_url)
        figure_element.replace_with(soup.new_tag("img", src=new_url))
    
    for ad in content_element.select(".ads-container, .inarticle-feed, .more-contents, iframe, figure"):
        ad.extract()

    link_elements = content_element.select("a")
    for link_element in link_elements:
        url = link_element.attrs.get("href")
        if "evrimagaci" in url.lower():
            link_element.replace_with(link_element.text)

    tooltip_elements = content_element.select(".dictionary-tooltip")
    for tooltip_element in tooltip_elements:
        tooltip_element.replace_with(tooltip_element.text)

    formula_elements = content_element.select(".ql-formula")
    for formula_element in formula_elements:
        formula_element.replace_with(formula_element["data-value"])

    content_element.attrs = {}

    content_html = str(content_element)
    
    references_elements = content_container.select(".content-references, .references ul, .content-references ul")
    references = [element.get_text(separator=" ").strip() for element in references_elements]
   
    match = re.search(r'-(\d+)$', article_url)
    article_id = match.group(1) if match else None

    return {
        "id": article_id,
        "title_html": title_html,
        "content_html": content_html,
        "references": references,
        "banner_url": new_banner_url
    }

titles = []
page = 0 
visited_pages = 0 

while True:
    time.sleep(2)  
    response = requests.post("https://evrimagaci.org/ajax/mars-content", {
        "page": page,
        "exclude_id": True,
        "tag_id": "ct0",
        "filters": '{"read_time":"","type":"","order":"1"}',
        "csrf_token_001": "3b46412924cda91cd5940d74505b7604"
    })

    jsondata = response.json()

    if not jsondata.get("status") or not jsondata.get("html"):
        print("All pages have been scanned or data cannot be retrieved.")
        break  

    soup = BeautifulSoup(jsondata.get("html"), "html.parser")

    elements = soup.select(".title>a")

    print(f"Page {page + 1} scanner...")

    for element in elements:
        title_text = element.text.strip()
        title_link = element.attrs.get("href")
        print(f"Title: {title_text}") 

        article_data = parse(title_link) 
        titles.append(article_data)

    page += 1 
    visited_pages += 1 


filename = "output.json"
if os.path.exists(filename):
    with open(filename, "r", encoding="utf-8") as file:
        existing_data = json.load(file)
        titles.extend(existing_data)

with open(filename, "w", encoding="utf-8") as file:
    json.dump(titles, file, ensure_ascii=False, indent=4)

print(f"Data was saved to file {filename}.")
print(f"Total number of pages visited: {visited_pages}")
