-- The delivered revenue and freight of fct_orders must equal the sum of their items in
-- fct_order_items. The test fails when it returns a row.
with

orders as (
    select
        sum(items_revenue_brl) as revenue_brl,
        sum(freight_value_brl) as freight_brl
    from {{ ref('fct_orders') }}
    where is_delivered
),

order_items as (
    select
        sum(price_brl) as revenue_brl,
        sum(freight_value_brl) as freight_brl
    from {{ ref('fct_order_items') }}
    where is_delivered
)

select
    orders.revenue_brl as orders_revenue_brl,
    order_items.revenue_brl as order_items_revenue_brl,
    orders.freight_brl as orders_freight_brl,
    order_items.freight_brl as order_items_freight_brl
from orders
cross join order_items
where
    orders.revenue_brl != order_items.revenue_brl
    or orders.freight_brl != order_items.freight_brl
