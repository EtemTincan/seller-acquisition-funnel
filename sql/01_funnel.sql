-- The funnel in numbers: leads -> signed -> sold at least once -> GMV.
SELECT (SELECT count(*) FROM lead)                                        AS leads,
       (SELECT count(*) FROM signed)                                      AS signed,
       (SELECT count(*) FROM seller_window_all)                           AS observed,
       (SELECT count(*) FROM seller_window_all WHERE orders_in_window > 0) AS activated,
       (SELECT sum(gmv_in_window) FROM seller_window_all)                 AS gmv,
       (SELECT max(gmv_in_window) FROM seller_window_all)                 AS top_seller_gmv,
       (SELECT median(first_sale_date - won_date)
          FROM seller_window_all WHERE first_sale_date IS NOT NULL)       AS median_days_to_first_sale;
