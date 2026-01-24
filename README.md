# Books Scraper

This is a simple Python project I made to practice web scraping. It collects information about books (like titles, prices, and ratings) from a demo website called [Books to Scrape](http://books.toscrape.com/) and saves the data into a CSV file.


## What It Does
- Scrapes book details:
  - Title
  - Price
  - Rating (e.g., 1–5 stars)
  - Availability (e.g., "In stock")
- Saves the data to a `books.csv` file in the same folder.

## What You Need
To run this project, you need:
- Python 3 installed on your computer
- Pip (Python’s package manager)

## How to Set It Up
1. Download the project to your computer:
   ```bash
   git clone https://github.com/ITZSAMI/Books-Scraper.git
   ```

2. Go into the project folder:
   ```bash
   cd Books-Scraper
   ```

3. (Optional) Create a virtual environment:
   ```bash
   python3 -m venv scraper-env
   source scraper-env/bin/activate
   ```

4. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run It
Run the script like this:
```bash
python books_scraper.py
```

The script will create a file called `books.csv` with all the book data inside.

## Example of the Output
Here’s what the `books.csv` file might look like when you open it:

| Title                        | Price   | Rating   | Availability   |
|------------------------------|---------|----------|----------------|
| The Grand Design             | £13.33  | 5 stars  | In stock       |
| The Art of Not Breathing     | £20.66  | 4 stars  | In stock       |

## Notes
- This project is for learning only. It works specifically with the [Books to Scrape](http://books.toscrape.com/) demo site.
- If you want to scrape another site, you’ll need to edit the code.

### Hope This Helps! 😊
