"""
Query cost validation rule. This is directly copied from
https://github.com/mirumee/ariadne/blob/master/ariadne/validation/query_cost.py
with small edits to have default multipliers for ["first", "last"] fields, and
every code concerning getting values from cost directive has been removed.
"""
from functools import reduce
from operator import add, mul
from typing import Any, Dict, List, Optional, Type, Union, cast

from graphql import (
    GraphQLError,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    get_named_type,
)
from graphql.execution.values import get_argument_values
from graphql.language import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    Node,
    OperationDefinitionNode,
    OperationType,
    StringValueNode,
)
from graphql.type import GraphQLFieldMap
from graphql.validation import ValidationContext
from graphql.validation.rules import ASTValidationRule, ValidationRule

cost_directive = """
directive @cost(complexity: Int, multipliers: [String!], useMultipliers: Boolean) on FIELD | FIELD_DEFINITION
"""

CostAwareNode = Union[
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    OperationDefinitionNode,
]


class CostValidator(ValidationRule):
    context: ValidationContext
    maximum_cost: int
    default_cost: int = 0
    default_complexity: int = 1
    variables: Optional[Dict] = None
    cost_map: Optional[Dict[str, Dict[str, Any]]] = None

    def __init__(
        self,
        context: ValidationContext,
        maximum_cost: int,
        *,
        default_cost: int = 0,
        default_complexity: int = 1,
        variables: Optional[Dict] = None,
        cost_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        super().__init__(context)

        self.maximum_cost = maximum_cost
        self.variables = variables
        self.cost_map = cost_map
        self.default_cost = default_cost
        self.default_complexity = default_complexity
        self.cost = 0
        self.operation_multipliers: List[Any] = []

    def compute_node_cost(self, node: CostAwareNode, type_def, parent_multipliers=None):
        if parent_multipliers is None:
            parent_multipliers = []
        if isinstance(node, FragmentSpreadNode) or not node.selection_set:
            return 0
        fields: GraphQLFieldMap = {}
        if isinstance(type_def, (GraphQLObjectType, GraphQLInterfaceType)):
            fields = type_def.fields
        total = 0
        for child_node in node.selection_set.selections:
            self.operation_multipliers = parent_multipliers[:]
            node_cost = self.default_cost
            if isinstance(child_node, FieldNode):
                field = fields.get(child_node.name.value)
                if not field:
                    continue
                field_type = get_named_type(field.type)
                try:
                    field_args: Dict[str, Any] = get_argument_values(
                        field, child_node, self.variables
                    )
                except Exception as e:
                    report_error(self.context, e)
                    field_args = {}
                cost_map_args = (
                    self.get_args_from_cost_map(child_node, type_def.name, field_args)
                    if type_def and type_def.name
                    else None
                )
                try:
                    node_cost = self.compute_cost(**cost_map_args)
                except (TypeError, ValueError) as e:
                    report_error(self.context, e)
                child_cost = self.compute_node_cost(
                    child_node, field_type, self.operation_multipliers
                )
                node_cost += child_cost
            if isinstance(child_node, FragmentSpreadNode):
                fragment = self.context.get_fragment(child_node.name.value)
                if fragment:
                    fragment_type = self.context.schema.get_type(
                        fragment.type_condition.name.value
                    )
                    node_cost = self.compute_node_cost(fragment, fragment_type)
            if isinstance(child_node, InlineFragmentNode):
                inline_fragment_type = type_def
                if child_node.type_condition and child_node.type_condition.name:
                    inline_fragment_type = self.context.schema.get_type(
                        child_node.type_condition.name.value
                    )
                node_cost = self.compute_node_cost(child_node, inline_fragment_type)
            total += node_cost
        return total

    def enter_operation_definition(
        self, node, key, parent, path, ancestors
    ):  # pylint: disable=unused-argument
        try:
            validate_cost_map(self.cost_map, self.context.schema)
        except GraphQLError as cost_map_error:
            self.context.report_error(cost_map_error)
            return

        if node.operation is OperationType.QUERY:
            self.cost += self.compute_node_cost(node, self.context.schema.query_type)
        if node.operation is OperationType.MUTATION:
            self.cost += self.compute_node_cost(node, self.context.schema.mutation_type)
        if node.operation is OperationType.SUBSCRIPTION:
            self.cost += self.compute_node_cost(
                node, self.context.schema.subscription_type
            )

    def leave_operation_definition(
        self, node, key, parent, path, ancestors
    ):  # pylint: disable=unused-argument
        if self.cost > self.maximum_cost:
            self.context.report_error(self.get_cost_exceeded_error())

    def compute_cost(self, multipliers=None, use_multipliers=True, complexity=None):
        if complexity is None:
            complexity = self.default_complexity
        if use_multipliers:
            if multipliers:
                multiplier = reduce(add, multipliers, 0)
                self.operation_multipliers = self.operation_multipliers + [multiplier]
            return reduce(mul, self.operation_multipliers, complexity)
        print(complexity)
        return complexity

    def get_args_from_cost_map(
        self, node: FieldNode, parent_type: str, field_args: Dict
    ):
        cost_args = None
        cost_map = cast(Dict[Any, Dict], self.cost_map)
        cost_args = cost_map.get(parent_type, {})
        cost_args = cost_args.copy()
        # have default multipliers
        cost_args["multipliers"] = cost_args.get("multiplers", ["first", "last"])
        cost_args["multipliers"] = self.get_multipliers_from_string(
            cost_args["multipliers"], field_args
        )
        return cost_args

    def get_multipliers_from_list_node(self, multipliers: List[Node], field_args):
        multipliers = [
            node.value  # type: ignore
            for node in multipliers
            if isinstance(node, StringValueNode)
        ]
        return self.get_multipliers_from_string(multipliers, field_args)  # type: ignore

    def get_multipliers_from_string(self, multipliers: List[str], field_args):
        accessors = [s.split(".") for s in multipliers]
        multipliers = []
        for accessor in accessors:
            val = field_args
            for key in accessor:
                val = val.get(key)
            try:
                multipliers.append(int(val))  # type: ignore
            except (ValueError, TypeError):
                pass
        multipliers = [
            len(multiplier) if isinstance(multiplier, (list, tuple)) else multiplier
            for multiplier in multipliers
        ]
        return [m for m in multipliers if m > 0]  # type: ignore

    def get_cost_exceeded_error(self) -> GraphQLError:
        return GraphQLError(
            cost_analysis_message(self.maximum_cost, self.cost),
            extensions={
                "cost": {
                    "requestedQueryCost": self.cost,
                    "maximumAvailable": self.maximum_cost,
                }
            },
        )


def validate_cost_map(cost_map: Dict[str, Dict[str, Any]], schema: GraphQLSchema):
    for type_name, type_fields in cost_map.items():
        if type_name not in schema.type_map:
            raise GraphQLError(
                "The query cost could not be calculated because cost map specifies a type "
                f"{type_name} that is not defined by the schema."
            )

        if not isinstance(schema.type_map[type_name], GraphQLObjectType):
            raise GraphQLError(
                "The query cost could not be calculated because cost map specifies a type "
                f"{type_name} that is defined by the schema, but is not an object type."
            )

        for field_name in type_fields:
            graphql_type = cast(GraphQLObjectType, schema.type_map[type_name])
            if field_name not in graphql_type.fields:
                raise GraphQLError(
                    "The query cost could not be calculated because cost map contains "
                    f"a field {field_name} not defined by the {type_name} type."
                )


def report_error(context: ValidationContext, error: Exception):
    context.report_error(GraphQLError(str(error), original_error=error))


def cost_analysis_message(maximum_cost: int, cost: int) -> str:
    return "The query exceeds the maximum cost of %d. Actual cost is %d" % (
        maximum_cost,
        cost,
    )


def cost_validator(
    maximum_cost: int,
    *,
    default_cost: int = 0,
    default_complexity: int = 1,
    variables: Optional[Dict] = None,
    cost_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Type[ASTValidationRule]:
    class _CostValidator(CostValidator):
        def __init__(self, context: ValidationContext):
            super().__init__(
                context,
                maximum_cost=maximum_cost,
                default_cost=default_cost,
                default_complexity=default_complexity,
                variables=variables,
                cost_map=cost_map,
            )

    return cast(Type[ASTValidationRule], _CostValidator)
