WITH ordered AS (
 SELECT date,symbol,price,
 LAG(price) OVER(PARTITION BY symbol ORDER BY date) AS previous_price
 FROM prices WHERE date <= :as_of
)
SELECT date,symbol,price,price/previous_price-1.0 AS simple_return
FROM ordered ORDER BY date,symbol;