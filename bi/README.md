# BI layer

Power BI and Tableau read the `marts` schema only. Every KPI is computed on delivered orders
(`is_delivered = true`), as defined in `dbt/models/marts/_kpi_docs.md`.

| Path | Content |
| --- | --- |
| `reference_kpis.sql` | Reference figures for the consistency check, run with `make kpis` |
| `export_marts.py` | CSV export of the marts for Tableau Public, run with `make export` |
| `powerbi/` | Power BI project (PBIP) |
| `Olist-analytics.twbx` | Tableau packaged workbook |

## Prerequisites

```bash
cp .env.example .env   # then set POSTGRES_PASSWORD
# copy the 9 Olist CSV files into data/
make all               # warehouse up, raw load, dbt build
make kpis              # reference figures
```

## Connection

| Setting | Value |
| --- | --- |
| Server | `localhost` (from a Windows VM on a Mac: the host IP, `192.168.64.1` with UTM, `10.211.55.2` with Parallels) |
| Port | `POSTGRES_PORT` from `.env` (default `5432`) |
| Database | `POSTGRES_DB` (default `olist`) |
| User / password | `POSTGRES_USER` / `POSTGRES_PASSWORD` from `.env` |
| Schema | `marts` |
| SSL | Off (local container) |

Tables: `fct_orders`, `fct_order_items`, `dim_customers`, `dim_products`, `dim_sellers`,
`dim_dates`.

## Power BI

Power BI Desktop runs on Windows only. Get data, PostgreSQL database, Import mode. If Power BI
asks for an encrypted connection, accept the unencrypted one.

### Model

Single direction, one to many relationships:

| From (one) | To (many) | State |
| --- | --- | --- |
| `dim_dates[date_day]` | `fct_orders[order_date]` | Active |
| `dim_dates[date_day]` | `fct_order_items[order_date]` | Active |
| `dim_customers[customer_unique_id]` | `fct_orders[customer_unique_id]` | Active |
| `dim_customers[customer_unique_id]` | `fct_order_items[customer_unique_id]` | Active |
| `dim_products[product_id]` | `fct_order_items[product_id]` | Active |
| `dim_sellers[seller_id]` | `fct_order_items[seller_id]` | Active |
| `dim_dates[date_day]` | `dim_customers[first_order_date]` | Inactive, used by `Nouveaux clients` |

Mark `dim_dates` as the date table (column `date_day`). Save as a Power BI project (PBIP) in
`bi/powerbi/`.

### Measures

```dax
Chiffre d'affaires =
CALCULATE ( SUM ( fct_orders[items_revenue_brl] ), fct_orders[is_delivered] = TRUE () )

Frais de port =
CALCULATE ( SUM ( fct_orders[freight_value_brl] ), fct_orders[is_delivered] = TRUE () )

Commandes =
CALCULATE ( DISTINCTCOUNT ( fct_orders[order_id] ), fct_orders[is_delivered] = TRUE () )

Panier moyen = DIVIDE ( [Chiffre d'affaires], [Commandes] )

Note moyenne =
CALCULATE ( AVERAGE ( fct_orders[review_score] ), fct_orders[is_delivered] = TRUE () )

Délai moyen =
CALCULATE ( AVERAGE ( fct_orders[delivery_days] ), fct_orders[is_delivered] = TRUE () )

Taux de retard =
DIVIDE ( CALCULATE ( [Commandes], fct_orders[is_late] = TRUE () ), [Commandes] )

CA articles =
CALCULATE ( SUM ( fct_order_items[price_brl] ), fct_order_items[is_delivered] = TRUE () )

Taux de réachat =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_customers ), dim_customers[is_repeat_customer] = TRUE () ),
    CALCULATE ( COUNTROWS ( dim_customers ), dim_customers[has_delivered_order] = TRUE () )
)

Nouveaux clients =
CALCULATE (
    COUNTROWS ( dim_customers ),
    dim_customers[has_delivered_order] = TRUE (),
    USERELATIONSHIP ( dim_customers[first_order_date], dim_dates[date_day] )
)
```

`CA articles` is the revenue by category (from `fct_order_items`); `Chiffre d'affaires` is the
order level revenue. Both give the same total, which `assert_revenue_reconciles_between_facts`
tests in dbt.

## Tableau

Tableau Desktop: PostgreSQL connector (it needs the PostgreSQL JDBC driver), SSL off. Tableau
Public cannot connect to PostgreSQL: run `make export` and use the text files in `bi/exports/`.

### Data source

Use relationships, not joins, with `fct_orders` as the root table:

| From | To | Fields |
| --- | --- | --- |
| `fct_orders` | `dim_customers` | `customer_unique_id` |
| `fct_orders` | `dim_dates` | `order_date` = `date_day` |
| `fct_orders` | `fct_order_items` | `order_id` |
| `fct_order_items` | `dim_products` | `product_id` |
| `fct_order_items` | `dim_sellers` | `seller_id` |

Add a data source filter `Is Delivered = True` (on `fct_orders`). Fields that exist in both
facts get a `(Fct Order Items)` suffix: use the `fct_orders` ones unless stated otherwise.

### Calculated fields

```text
Chiffre d'affaires  SUM([Items Revenue Brl])
Commandes           COUNTD([Order Id])
Panier moyen        SUM([Items Revenue Brl]) / COUNTD([Order Id])
Note moyenne        AVG([Review Score])
Frais de port       SUM([Freight Value Brl])
Délai moyen         AVG([Delivery Days])
Taux de retard      COUNTD(IIF([Is Late], [Order Id], NULL)) / COUNTD([Order Id])
CA articles         SUM([Price Brl])
Taux de réachat     SUM(INT([Is Repeat Customer])) / SUM(INT([Has Delivered Order]))
Nouveaux clients    COUNTD([Customer Unique Id]), by MONTH([First Order Date])
```

`Taux de réachat` must be computed in a sheet that uses `dim_customers` alone, so that Tableau
counts customers and not orders. Save the workbook as `bi/Olist-analytics.twbx` and
publish it to Tableau Public.

## Dashboard

| Page | Content |
| --- | --- |
| Overview | KPI cards (revenue, orders, average basket, average review score), monthly revenue, top 10 categories |
| Logistics | Average delivery time, late rate by customer state, review score on time vs late |
| Customers | Repeat purchase rate, customers by state, new customers per month |

## Consistency check

Full dataset, delivered orders. SQL values come from `make kpis`.

| KPI | SQL | Power BI | Tableau |
| --- | ---: | ---: | ---: |
| Revenue (BRL) | 13,221,498.11 | | |
| Orders | 96,478 | | |
| Average basket (BRL) | 137.04 | | |
| Average review score | 4.16 | | |

Other reference figures: freight 2,198,275.64 BRL, average delivery time 12.50 days, late rate
6.77 %, repeat purchase rate 3.00 %.
