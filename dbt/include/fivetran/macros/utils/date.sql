{% macro fivetran__dateadd(datepart, interval, from_date_or_timestamp) %}

    date_add({{ from_date_or_timestamp }}, interval ({{ interval }}) {{ datepart }})

{% endmacro %}

{% macro fivetran__datediff(first_date, second_date, datepart) -%}
    {% if datepart == 'week' %}
            ({{ datediff(first_date, second_date, 'day') }} // 7 + case
            when date_part('dow', ({{first_date}})::timestamp) <= date_part('dow', ({{second_date}})::timestamp) then
                case when {{first_date}} <= {{second_date}} then 0 else -1 end
            else
                case when {{first_date}} <= {{second_date}} then 1 else 0 end
        end)
    {% else %}
        (date_diff('{{ datepart }}', {{ first_date }}::timestamp, {{ second_date}}::timestamp ))
    {% endif %}
{%- endmacro %}

{% macro fivetran__last_day(date, datepart) -%}

    {%- if datepart == 'quarter' -%}
    -- duckdb dateadd does not support quarter interval.
    cast(
        {{dbt.dateadd('day', '-1',
        dbt.dateadd('month', '3', dbt.date_trunc(datepart, date))
        )}}
        as date)
    {%- else -%}
    {{dbt.default_last_day(date, datepart)}}
    {%- endif -%}

{%- endmacro %}

