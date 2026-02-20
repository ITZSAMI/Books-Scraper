# Books Scraper

Python script for scraping book data from http://books.toscrape.com  
The extracted data is exported to a CSV file.


## Overview

This project demonstrates basic web scraping techniques using Python.
It retrieves book information across multiple pages and stores the results
in a structured format.


## Extracted Data

For each book, the following information is collected:

- Title
- Price
- Rating
- Availability

The data is saved in a file named:

books.csv


## Technologies Used

- Python 3
- requests
- BeautifulSoup (bs4)
- pandas


## Project Structure
```
.
├── books_scraper.py
├── requirements.txt
└── .gitignore

```

## Installation

Clone the repository:
git clone https://github.com/ITZSAMI/Books-Scraper.git
cd Books-Scraper

Install dependencies: pip install -r requirements.txt



## Usage

Run the script: python books_scraper.py


The script iterates through all available catalogue pages and generates
a CSV file containing the collected book data.


## Purpose

This project was created to practice:

- HTTP requests handling
- HTML parsing and DOM navigation
- Pagination handling
- Data structuring with pandas
- Writing modular Python scripts


## Notes

The website used in this project (books.toscrape.com) is specifically
designed for practicing web scraping.



