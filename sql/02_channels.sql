-- Channel scorecard: volume, win rate, activation and revenue per signed seller.
-- gmv_per_100_leads chains the two stages so channels can be compared on one
-- number: revenue produced per 100 leads that enter the funnel.
WITH lead_stage AS (
    SELECT l.channel,
           count(*)        AS leads,
           count(d.mql_id) AS signed
    FROM lead l
    LEFT JOIN deals d USING (mql_id)
    GROUP BY 1
),
sales_stage AS (
    SELECT channel,
           count(*)                                     AS observed,
           count(*) FILTER (WHERE orders_in_window > 0) AS activated,
           sum(gmv_in_window)                           AS gmv
    FROM seller_window
    GROUP BY 1
)
SELECT a.channel,
       a.leads,
       a.leads / sum(a.leads) OVER ()                            AS lead_share,
       a.signed,
       a.signed / a.leads::DOUBLE                                AS win_rate,
       b.observed,
       b.activated,
       b.activated / b.observed::DOUBLE                          AS activation_rate,
       b.gmv / b.observed                                        AS gmv_per_signed,
       100 * (a.signed / a.leads::DOUBLE) * (b.gmv / b.observed) AS gmv_per_100_leads
FROM lead_stage a
LEFT JOIN sales_stage b USING (channel)
ORDER BY a.leads DESC;
