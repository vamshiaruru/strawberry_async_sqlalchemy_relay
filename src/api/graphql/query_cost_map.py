"""
Costs Map used by query complexity validator rule. Find more info here:
https://ariadnegraphql.org/docs/0.14.0/query-validators#setting-default-field-cost-and-complexity

BY DEFAULT, every field has complexity of 1, multipliers are applied by default
on the "first" and "last" fields. So only update the below dictionary IF you want
to override this default behaviour.
"""
COST_MAP = {}
