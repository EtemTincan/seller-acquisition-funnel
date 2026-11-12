-- Base views shared by every query.
--
-- $cutoff   = last day with complete order data (2018-08-31)
-- $window   = days after signing in which a seller's sales are measured
-- $skip_top = 1 to leave the single largest seller out of sales metrics, else 0
--
-- A seller only counts in sales metrics if we could watch them for the full
-- window. Someone signed 20 days before the data ends has not "failed to sell
-- in 90 days" - we simply cannot see it yet. Dropping them avoids that bias.

CREATE OR REPLACE VIEW lead AS
SELECT mql_id,
       first_contact_date,
       landing_page_id,
       CASE origin
            WHEN 'organic_search' THEN 'Organic search'
            WHEN 'paid_search'    THEN 'Paid search'
            WHEN 'social'         THEN 'Social'
            WHEN 'direct_traffic' THEN 'Direct'
            WHEN 'email'          THEN 'Email'
            WHEN 'referral'       THEN 'Referral'
            WHEN 'unknown'        THEN 'Unattributed'
            ELSE 'Other sources'  -- display, other, other_publicities: 333 leads in total
       END AS channel
FROM leads;

CREATE OR REPLACE VIEW signed AS
SELECT d.seller_id,
       l.channel,
       l.first_contact_date,
       d.won_date,
       date_diff('day', l.first_contact_date, d.won_date)             AS days_to_sign,
       d.lead_type,
       d.business_type,
       d.won_date <= CAST($cutoff AS DATE) - CAST($window AS INTEGER) AS observable
FROM deals d
JOIN lead l USING (mql_id);

CREATE OR REPLACE VIEW seller_window_all AS
SELECT s.seller_id,
       s.channel,
       s.won_date,
       s.lead_type,
       s.business_type,
       count(DISTINCT x.order_id)   AS orders_in_window,
       COALESCE(sum(x.price), 0)    AS gmv_in_window,
       min(x.order_date)            AS first_sale_date
FROM signed s
LEFT JOIN sales x
       ON x.seller_id = s.seller_id
      AND x.order_date >= s.won_date
      AND x.order_date <  s.won_date + CAST($window AS INTEGER)
WHERE s.observable
GROUP BY ALL;

CREATE OR REPLACE VIEW seller_window AS
SELECT *
FROM seller_window_all
QUALIFY row_number() OVER (ORDER BY gmv_in_window DESC, seller_id) > $skip_top;
