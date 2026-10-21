with

days as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2016-01-01' as date)",
        end_date="cast('2019-01-01' as date)"
    ) }}
)

select
    cast(date_day as date) as date_day,
    cast(extract(year from date_day) as integer) as year_number,
    cast(extract(quarter from date_day) as integer) as quarter_number,
    cast(extract(month from date_day) as integer) as month_number,
    to_char(date_day, 'FMMonth') as month_name,
    cast(date_trunc('month', date_day) as date) as month_start,
    cast(extract(isodow from date_day) as integer) as iso_day_of_week,
    to_char(date_day, 'FMDay') as day_name,
    extract(isodow from date_day) in (6, 7) as is_weekend
from days
