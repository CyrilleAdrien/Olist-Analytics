-- One row per person (customer_unique_id), not per customer_id, which changes with every order
with

customers as (
    select * from {{ ref('stg_olist__customers') }}
),

orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customer_orders as (
    select
        customers.customer_unique_id,
        customers.customer_zip_code_prefix,
        customers.customer_city,
        customers.customer_state,
        orders.order_id,
        orders.order_status,
        orders.order_purchased_at,
        row_number() over (
            partition by customers.customer_unique_id
            order by orders.order_purchased_at desc, orders.order_id asc
        ) as recency_rank
    from customers
    inner join orders
        on customers.customer_id = orders.customer_id
),

aggregated as (
    select
        customer_unique_id,
        min(order_purchased_at) as first_order_at,
        max(order_purchased_at) as last_order_at,
        count(*) as orders_count,
        count(*) filter (where order_status = 'delivered') as delivered_orders_count
    from customer_orders
    group by customer_unique_id
),

-- A person can order from several addresses: keep the one of the most recent order
latest_address as (
    select
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state
    from customer_orders
    where recency_rank = 1
)

select
    aggregated.customer_unique_id,
    latest_address.customer_zip_code_prefix,
    latest_address.customer_city,
    latest_address.customer_state,
    aggregated.first_order_at,
    cast(aggregated.first_order_at as date) as first_order_date,
    aggregated.last_order_at,
    aggregated.orders_count,
    aggregated.delivered_orders_count,
    aggregated.delivered_orders_count >= 1 as has_delivered_order,
    aggregated.delivered_orders_count >= 2 as is_repeat_customer
from aggregated
inner join latest_address
    on aggregated.customer_unique_id = latest_address.customer_unique_id
