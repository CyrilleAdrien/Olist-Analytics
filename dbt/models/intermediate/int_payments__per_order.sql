with

payments as (
    select * from {{ ref('stg_olist__payments') }}
),

ranked as (
    select
        *,
        -- Main payment type: the one that paid the largest amount
        row_number() over (
            partition by order_id
            order by payment_value_brl desc, payment_sequential asc
        ) as payment_rank
    from payments
),

aggregated as (
    select
        order_id,
        sum(payment_value_brl) as payment_value_brl,
        count(*) as payment_count,
        max(payment_installments) as payment_installments,
        max(case when payment_rank = 1 then payment_type end) as main_payment_type
    from ranked
    group by order_id
)

select * from aggregated
