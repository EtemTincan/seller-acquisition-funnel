-- Signing-month cohorts: share of sellers with at least one sale in each
-- 30-day period after signing. A cell is only shown when every seller in the
-- cohort could be observed for that whole period.
WITH periods AS (SELECT unnest(range(0, 7)) AS period),
cohort AS (
    SELECT seller_id, won_date, date_trunc('month', won_date) AS cohort_month
    FROM signed
),
grid AS (
    SELECT c.cohort_month, p.period, c.seller_id, c.won_date
    FROM cohort c CROSS JOIN periods p
),
active AS (
    SELECT g.cohort_month, g.period, g.seller_id,
           count(x.order_id) > 0 AS sold
    FROM grid g
    LEFT JOIN sales x
           ON x.seller_id = g.seller_id
          AND x.order_date >= g.won_date + CAST(30 * g.period AS INTEGER)
          AND x.order_date <  g.won_date + CAST(30 * (g.period + 1) AS INTEGER)
    GROUP BY ALL
)
SELECT a.cohort_month,
       a.period,
       count(*)                      AS sellers,
       avg(a.sold::INT)              AS share_selling
FROM active a
JOIN (SELECT cohort_month, max(won_date) AS last_won FROM cohort GROUP BY 1) m
  USING (cohort_month)
WHERE m.last_won + CAST(30 * (a.period + 1) AS INTEGER) <= CAST($cutoff AS DATE) + 1
GROUP BY 1, 2
HAVING count(*) >= 20
ORDER BY 1, 2;
