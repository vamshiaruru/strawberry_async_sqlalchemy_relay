"""Base dataloader class all dataloaders should inherit from"""
from typing import Any, List

import aiodataloader


class DataLoader(aiodataloader.DataLoader):
    """
    The main purpose of this class is to cache dataloaders at request level.
    We want only one instance of a specific dataloader to be used at any time in
    one request. So we cach dataloaders in context, as new context is created on
    every request.
    """

    order_key = None
    context_key = None
    context = None
    get_cache_key_fn = lambda self, x: x  # noqa: E731

    def __new__(cls, context):
        """
        Create a new dataloader object only if the object hasn't already been
        created.
        """
        key = cls.context_key
        if key is None:
            raise TypeError(f"Data loader {cls} does not define context key")
        if "dataloaders" not in context:
            context["dataloaders"] = {}
        if key not in context["dataloaders"]:
            # cache if not already cached. Otherwise return the already created
            # dataloader
            context["dataloaders"][key] = super().__new__(cls)
        return context["dataloaders"][key]

    def __init__(self, context, *args, **kwargs):
        """When initialising a new dataloader, if context has changed, update it"""
        if self.context != context:
            self.context = context
            kwargs["get_cache_key"] = self.get_cache_key_fn
            super().__init__(*args, **kwargs)

    async def load_many(
        self,
        keys: List[Any],
        ensure_order: bool = True,
    ):
        """Overriding to return results in the same order as input"""
        keys = list(keys)
        results = await super().load_many(keys=keys)
        if ensure_order:
            results = self.ensure_order(keys, results)
        return results

    async def batch_load_fn(self, keys):
        raise NotImplementedError

    def get_serializable_key_for_result(self, result):
        if type(self.order_key) == str:
            return self.get_cache_key(getattr(result, self.order_key))
        elif type(self.order_key) == tuple:
            _key = {k: getattr(result, k) for k in result}
            return self.get_cache_key(_key)
        else:
            raise NotImplementedError(
                f"Cannot gaurantee order for: {type(self.order_key)}"
            )

    def ensure_order(self, keys, results):
        if not self.order_key:
            raise Exception("Cannot order without an order key")
        key_result_map = {
            self.get_serializable_key_for_result(result): result for result in results
        }
        return [key_result_map[self.get_cache_key(key)] for key in keys]
