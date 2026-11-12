-- How long a lead takes to sign, per channel.
SELECT channel,
       count(*)                       AS signed,
       median(days_to_sign)           AS median_days,
       avg((days_to_sign <= 30)::INT) AS share_within_30d
FROM signed
WHERE days_to_sign >= 0
GROUP BY 1
ORDER BY median_days;
