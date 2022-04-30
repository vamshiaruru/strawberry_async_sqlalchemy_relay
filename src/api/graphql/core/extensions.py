from graphql_relay import to_global_id
from strawberry.extensions import Extension


class RelayIdExtension(Extension):
    """Modifies id fields with type strawberry.ID to relay id"""

    def resolve(self, _next, root, info, *args, **kwargs):
        result = _next(root, info, *args, **kwargs)
        if info.field_name == "id" and str(info.return_type) == "ID!":
            return to_global_id(info.parent_type.name, result)
        return result
