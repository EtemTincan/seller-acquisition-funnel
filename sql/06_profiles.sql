-- Which kind of seller pays off, using the profile the sales team recorded
-- at signing. Two cuts stacked into one result: lead type and business type.
SELECT 'Lead type'                              AS dimension,
       replace(lead_type, '_', ' ')             AS profile,
       count(*)                                 AS observed,
       avg((orders_in_window > 0)::INT)         AS activation_rate,
       sum(gmv_in_window) / count(*)            AS gmv_per_signed
FROM seller_window
WHERE lead_type IS NOT NULL
GROUP BY 1, 2
HAVING count(*) >= 10

UNION ALL

SELECT 'Business type',
       business_type,
       count(*),
       avg((orders_in_window > 0)::INT),
       sum(gmv_in_window) / count(*)
FROM seller_window
WHERE business_type IN ('reseller', 'manufacturer')
GROUP BY 1, 2
ORDER BY 1 DESC, 4 DESC;
