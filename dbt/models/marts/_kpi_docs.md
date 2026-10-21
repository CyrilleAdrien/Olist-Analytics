{% docs kpi_revenue %}
**Revenue (BRL)**: sum of the item prices (`price`) of the order, shipping excluded.
The KPI only counts delivered orders (`is_delivered = true`).
{% enddocs %}

{% docs kpi_freight %}
**Freight (BRL)**: sum of the shipping costs (`freight_value`) of the order items.
Same scope as revenue: delivered orders only.
{% enddocs %}

{% docs kpi_orders %}
**Orders**: distinct count of `order_id` among delivered orders.
{% enddocs %}

{% docs kpi_average_basket %}
**Average basket (BRL)**: revenue divided by the number of orders, computed after
aggregation. Never an average of per-order averages.
{% enddocs %}

{% docs kpi_delivery_days %}
**Delivery time (days)**: calendar days between the purchase date and the date the customer
received the order. Only for delivered orders with both dates known: 8 delivered orders have
no delivery date and are left out.
{% enddocs %}

{% docs kpi_late_rate %}
**Late delivery rate**: delivered orders received after the estimated delivery date, compared
day by day, divided by delivered orders. `is_late` is false for orders that were not delivered
or whose delivery date is unknown.
{% enddocs %}

{% docs kpi_review_score %}
**Average review score (1 to 5)**: average of `review_score`, with one review per order: the
most recently answered one. An order can receive several reviews, and counting all of them
would weigh some orders twice.
{% enddocs %}

{% docs kpi_repeat_rate %}
**Repeat purchase rate**: customers with 2 delivered orders or more, divided by customers with
at least one delivered order. A customer is a `customer_unique_id`, because Olist creates a new
`customer_id` for every order: counting `customer_id` would show almost no repeat customers.
{% enddocs %}
