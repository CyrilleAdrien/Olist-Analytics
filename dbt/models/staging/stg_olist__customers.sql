with

source as (
    select * from {{ source('olist', 'customers') }}
),

renamed as (
    select
        customer_id,
        customer_unique_id,
        -- Kept as text: zip code prefixes have leading zeros
        customer_zip_code_prefix,
        customer_city,
        customer_state
    from source
)

select * from renamed
