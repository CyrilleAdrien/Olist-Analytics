"""Stand-ins for the dbt_utils macros used in the models, for sqlfluff's jinja templater.

They only need to render valid SQL of the same shape: dbt renders the real macros.
"""


def generate_surrogate_key(field_list):
    return "md5(" + " || '-' || ".join(f"cast({field} as text)" for field in field_list) + ")"


def date_spine(datepart, start_date, end_date):
    step = f"interval '1 {datepart}'"
    return f"select generate_series({start_date}, {end_date}, {step}) as date_{datepart}"
