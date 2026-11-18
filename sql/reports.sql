-- Report queries. Each one starts with a "-- name:" line so the CLI can run
-- them by name:  python -m books_etl report <name>

-- name: price_by_rating
-- Average, cheapest and dearest price for each star rating.
SELECT rating,
       COUNT(*)                            AS books,
       ROUND(AVG(price_pence) / 100.0, 2)  AS avg_price,
       MIN(price_pence) / 100.0            AS min_price,
       MAX(price_pence) / 100.0            AS max_price
FROM books
GROUP BY rating
ORDER BY rating;

-- name: top_per_rating
-- The three most expensive books within each rating (window function).
SELECT rating, rank, title, price
FROM (
    SELECT rating,
           title,
           price_pence / 100.0 AS price,
           ROW_NUMBER() OVER (PARTITION BY rating ORDER BY price_pence DESC) AS rank
    FROM books
)
WHERE rank <= 3
ORDER BY rating, rank;

-- name: price_bands
-- How many books fall into each price band, and their share of the catalogue.
SELECT CASE
           WHEN price_pence < 2000 THEN '1: under 20'
           WHEN price_pence < 4000 THEN '2: 20-40'
           ELSE '3: 40 and over'
       END                                                      AS band,
       COUNT(*)                                                 AS books,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)       AS pct
FROM books
GROUP BY band
ORDER BY band;

-- name: price_changes
-- Books whose price changed between runs, with the before and after.
SELECT b.title,
       h.recorded_at,
       LAG(h.price_pence) OVER (PARTITION BY h.url ORDER BY h.recorded_at) / 100.0 AS old_price,
       h.price_pence / 100.0                                                       AS new_price
FROM price_history h
JOIN books b ON b.url = h.url
WHERE h.url IN (SELECT url FROM price_history GROUP BY url HAVING COUNT(*) > 1)
ORDER BY b.title, h.recorded_at;

-- name: run_history
-- The last ten pipeline runs.
SELECT run_id, started_at, status, rows_extracted, rows_loaded, rows_rejected, error
FROM etl_runs
ORDER BY started_at DESC
LIMIT 10;
