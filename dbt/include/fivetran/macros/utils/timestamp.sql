
{% macro fivetran__current_timestamp() -%}
  now()
{%- endmacro %}

{% macro fivetran__snapshot_string_as_time(timestamp) -%}
    {%- set result = "'" ~ timestamp ~ "'::timestamp" -%}
    {{ return(result) }}
{%- endmacro %}

{% macro fivetran__snapshot_get_time() -%}
  {{ current_timestamp() }}::timestamp
{%- endmacro %}
