with

orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customers as (
    select * from {{ ref('stg_olist__customers') }}
),

items as (
    select
        order_id,
        count(*) as items_count,
        sum(price_brl) as items_revenue_brl,
        sum(freight_value_brl) as freight_value_brl
    from {{ ref('stg_olist__order_items') }}
    group by order_id
),

payments as (
    select * from {{ ref('int_payments__per_order') }}
),

reviews as (
    select * from {{ ref('int_reviews__latest_per_order') }}
),

joined as (
    select
        orders.order_id,
        orders.customer_id,
        customers.customer_unique_id,
        orders.order_status,
        orders.order_status = 'delivered' as is_delivered,
        orders.order_purchased_at,
        cast(orders.order_purchased_at as date) as order_date,
        orders.order_approved_at,
        orders.order_delivered_carrier_at,
        orders.order_delivered_customer_at,
        orders.order_estimated_delivery_at,
        coalesce(items.items_count, 0) as items_count,
        coalesce(items.items_revenue_brl, 0) as items_revenue_brl,
        coalesce(items.freight_value_brl, 0) as freight_value_brl,
        payments.payment_value_brl,
        payments.payment_count,
        payments.payment_installments,
        payments.main_payment_type,
        reviews.review_id,
        reviews.review_score,
        coalesce(reviews.review_count, 0) as review_count
    from orders
    inner join customers
        on orders.customer_id = customers.customer_id
    left join items
        on orders.order_id = items.order_id
    left join payments
        on orders.order_id = payments.order_id
    left join reviews
        on orders.order_id = reviews.order_id
)

select
    *,
    -- Delivery metrics only make sense for delivered orders with a known delivery date
    case
        when is_delivered and order_delivered_customer_at is not null
            then cast(order_delivered_customer_at as date) - order_date
    end as delivery_days,
    coalesce(
        is_delivered
        and cast(order_delivered_customer_at as date)
        > cast(order_estimated_delivery_at as date),
        false
    ) as is_late
from joined
