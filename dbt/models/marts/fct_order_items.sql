with

order_items as (
    select
        *,
        {{ dbt_utils.generate_surrogate_key(['order_id', 'order_item_id']) }} as order_item_key
    from {{ ref('stg_olist__order_items') }}
),

orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customers as (
    select * from {{ ref('stg_olist__customers') }}
)

select
    order_items.order_item_key,
    order_items.order_id,
    order_items.order_item_id,
    order_items.product_id,
    order_items.seller_id,
    customers.customer_unique_id,
    cast(orders.order_purchased_at as date) as order_date,
    orders.order_status,
    orders.order_status = 'delivered' as is_delivered,
    order_items.shipping_limit_at,
    order_items.price_brl,
    order_items.freight_value_brl
from order_items
inner join orders
    on order_items.order_id = orders.order_id
inner join customers
    on orders.customer_id = customers.customer_id
