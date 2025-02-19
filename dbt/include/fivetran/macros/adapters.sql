{% macro fivetran__create_table_as(temporary, relation, sql) %}
    {% set _ignored = adapter.create_table_as(temporary, relation, sql) %}
{% endmacro %}

{% macro fivetran__rename_relation(from_relation, to_relation) -%}
  {% set target_name = adapter.quote_as_configured(to_relation.identifier, 'identifier') %}
  {% call statement('rename_relation') -%}
    alter {{ to_relation.type }} {{ from_relation }} rename to {{ target_name }}
  {%- endcall %}
{% endmacro %}

{% macro fivetran__list_relations_without_caching(schema_relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True) -%}
    select
      '{{ schema_relation.database }}' as database,
      table_name as name,
      table_schema as schema,
      CASE table_type
        WHEN 'VIEW' THEN 'view'
        END as type
    from system.information_schema.tables
    where lower(table_schema) = '{{ schema_relation.schema | lower }}'
    and lower(table_catalog) = '{{ schema_relation.database | lower }}'
  {% endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}


{% macro fivetran__source(source_name, table_name) %}
    {# Call the default source macro to handle the lookup in sources.yml #}
    {% set source_relation = builtins.source(source_name, table_name) %}
    {% set relation = adapter.handle_source(source_relation) %}
    {{ return(relation) }}
{% endmacro %}

{% macro source(source_name, table_name) %}
    {% set relation = adapter.dispatch('source')(source_name, table_name) %}
    {{ return(relation) }}
{% endmacro %}