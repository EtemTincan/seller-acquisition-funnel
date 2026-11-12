-- Do sellers who are silent for 90 days start selling later?
-- Only sellers signed at least 180 days before the data ends, so that both
-- halves (days 1-90 and days 91-180) are fully observed for everyone.
WITH watched AS (
    SELECT seller_id, won_date
    FROM signed
    WHERE won_date <= CAST($cutoff AS DATE) - 180
),
halves AS (
    SELECT w.seller_id,
           count(*) FILTER (WHERE x.order_date <  w.won_date + 90)  AS early_items,
           count(*) FILTER (WHERE x.order_date >= w.won_date + 90
                              AND x.order_date <  w.won_date + 180) AS late_items
    FROM watched w
    LEFT JOIN sales x USING (seller_id)
    GROUP BY 1
)
SELECT count(*)                                                  AS sellers,
       count(*) FILTER (WHERE early_items = 0)                   AS silent_at_90,
       count(*) FILTER (WHERE early_items = 0 AND late_items > 0) AS late_starters,
       count(*) FILTER (WHERE early_items > 0)                   AS selling_at_90,
       count(*) FILTER (WHERE early_items > 0 AND late_items > 0) AS still_selling
FROM halves;
