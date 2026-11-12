-- How concentrated revenue is: sellers ranked by GMV, with running share.
-- Uses every observable seller, including the largest one.
SELECT row_number() OVER (ORDER BY gmv_in_window DESC, seller_id)       AS seller_rank,
       gmv_in_window,
       sum(gmv_in_window) OVER (ORDER BY gmv_in_window DESC, seller_id)
         / sum(gmv_in_window) OVER ()                                   AS cumulative_gmv_share,
       row_number() OVER (ORDER BY gmv_in_window DESC, seller_id)
         / count(*) OVER ()::DOUBLE                                     AS cumulative_seller_share
FROM seller_window_all
ORDER BY seller_rank;
