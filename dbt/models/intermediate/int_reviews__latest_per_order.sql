-- An order can have several reviews: keep the most recent answer, so that every order counts once
with

reviews as (
    select * from {{ ref('stg_olist__reviews') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by review_answered_at desc, review_created_at desc, review_id asc
        ) as review_rank,
        count(*) over (partition by order_id) as review_count
    from reviews
)

select
    order_id,
    review_id,
    review_score,
    review_created_at,
    review_answered_at,
    review_count
from ranked
where review_rank = 1
