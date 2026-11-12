-- Distribution of time-to-sign across all channels.
SELECT CASE WHEN days_to_sign <= 7   THEN 1
            WHEN days_to_sign <= 30  THEN 2
            WHEN days_to_sign <= 90  THEN 3
            WHEN days_to_sign <= 180 THEN 4
            ELSE 5 END                                   AS bucket_order,
       CASE WHEN days_to_sign <= 7   THEN 'Within a week'
            WHEN days_to_sign <= 30  THEN '8 to 30 days'
            WHEN days_to_sign <= 90  THEN '1 to 3 months'
            WHEN days_to_sign <= 180 THEN '3 to 6 months'
            ELSE 'Over 6 months' END                     AS bucket,
       count(*)                                          AS signed,
       count(*) / sum(count(*)) OVER ()                  AS share
FROM signed
WHERE days_to_sign >= 0
GROUP BY 1, 2
ORDER BY 1;
