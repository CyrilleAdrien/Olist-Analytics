-- Reference figures for the consistency check between SQL, Power BI and Tableau.
-- Every KPI is computed on delivered orders, from the marts schema only.
-- Run it with: make kpis

\echo '== 1. Consistency check: the 4 KPIs compared in the README'
select
    sum(items_revenue_brl) as revenue_brl,
    count(distinct order_id) as orders,
    round(sum(items_revenue_brl) / count(distinct order_id), 2) as average_basket_brl,
    round(avg(review_score), 2) as average_review_score
from marts.fct_orders
where is_delivered;

\echo '== 2. Other overview and logistics KPIs'
select
    sum(freight_value_brl) as freight_brl,
    round(avg(delivery_days), 2) as average_delivery_days,
    round(100.0 * count(*) filter (where is_late) / count(*), 2) as late_rate_pct
from marts.fct_orders
where is_delivered;

\echo '== 3. Repeat purchase rate'
select
    round(
        100.0 * count(*) filter (where is_repeat_customer)
        / count(*) filter (where has_delivered_order),
        2
    ) as repeat_rate_pct
from marts.dim_customers;

\echo '== 4. Monthly revenue (first and last 3 months)'
(
    select d.month_start, sum(o.items_revenue_brl) as revenue_brl
    from marts.fct_orders as o
    inner join marts.dim_dates as d on o.order_date = d.date_day
    where o.is_delivered
    group by d.month_start
    order by d.month_start
    limit 3
)
union all
(
    select d.month_start, sum(o.items_revenue_brl) as revenue_brl
    from marts.fct_orders as o
    inner join marts.dim_dates as d on o.order_date = d.date_day
    where o.is_delivered
    group by d.month_start
    order by d.month_start desc
    limit 3
)
order by month_start;

\echo '== 5. Top 10 categories by revenue'
select
    p.product_category_name_english as category,
    sum(i.price_brl) as revenue_brl
from marts.fct_order_items as i
inner join marts.dim_products as p on i.product_id = p.product_id
where i.is_delivered
group by p.product_category_name_english
order by revenue_brl desc
limit 10;

\echo '== 6. Late delivery rate by customer state (5 highest)'
select
    c.customer_state,
    count(*) as delivered_orders,
    round(100.0 * count(*) filter (where o.is_late) / count(*), 2) as late_rate_pct
from marts.fct_orders as o
inner join marts.dim_customers as c on o.customer_unique_id = c.customer_unique_id
where o.is_delivered
group by c.customer_state
order by late_rate_pct desc
limit 5;

\echo '== 7. Review score by delivery punctuality'
select
    o.is_late,
    count(*) as delivered_orders,
    round(avg(o.review_score), 2) as average_review_score
from marts.fct_orders as o
where o.is_delivered
group by o.is_late
order by o.is_late;

\echo '== 8. New customers per month (customers with a delivered order): 3 biggest months'
select
    d.month_start,
    count(*) as new_customers
from marts.dim_customers as c
inner join marts.dim_dates as d on c.first_order_date = d.date_day
where c.has_delivered_order
group by d.month_start
order by new_customers desc
limit 3;
