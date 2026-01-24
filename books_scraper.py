import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_books():
    base_url = "http://books.toscrape.com/catalogue/page-{}.html"
    page = 1
    books_data = []

    while True:
        url = base_url.format(page)
        response = requests.get(url)

        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        books = soup.find_all("article", class_="product_pod")

        if not books:
            break

        for book in books:
            title = book.h3.a["title"]
            price = book.find("p", class_="price_color").text
            rating = book.p["class"][1]
            availability = book.find("p", class_="instock availability").text.strip()
            books_data.append({
                "Title": title,
                "Price": price,
                "Rating": rating,
                "Availability": availability
            })

        page += 1

    df = pd.DataFrame(books_data)
    df.to_csv("books.csv", index=False)

if __name__ == "__main__":
    scrape_books()