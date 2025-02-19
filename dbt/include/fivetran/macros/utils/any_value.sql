{% macro fivetran__any_value(expression) -%}

    arbitrary({{ expression }})

{%- endmacro %}
