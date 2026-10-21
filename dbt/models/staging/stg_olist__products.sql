with

source as (
    select * from {{ source('olist', 'products') }}
),

translations as (
    select * from {{ ref('stg_olist__category_translation') }}
),

renamed as (
    select
        source.product_id,
        source.product_category_name,
        -- 2 categories have no translation: keep their Portuguese name rather than a null
        coalesce(
            translations.product_category_name_english,
            source.product_category_name,
            'unknown'
        ) as product_category_name_english,
        -- The source spells "length" as "lenght"
        cast(source.product_name_lenght as integer) as product_name_length,
        cast(source.product_description_lenght as integer) as product_description_length,
        cast(source.product_photos_qty as integer) as product_photos_qty,
        cast(source.product_weight_g as integer) as product_weight_g,
        cast(source.product_length_cm as integer) as product_length_cm,
        cast(source.product_height_cm as integer) as product_height_cm,
        cast(source.product_width_cm as integer) as product_width_cm
    from source
    left join translations
        on source.product_category_name = translations.product_category_name
)

select * from renamed
