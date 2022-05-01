# strawberry_async_sqlalchemy_relay
This repository contains a demo for a sample project that uses strawberry for graphql, fastapi with uvicorn as a web server, sqlachemy as the ORM/db toolkit. We use asyc version of sqlalchemy, and our graphql queries support relay style pagination. Alembic is used for database migrations.
Note that this server isn't fully relay compliant. We don't have a root level node query that fetches any resource based on the global ID.

## Prereqs
- Install postgres and get it running.
- Install poetry - https://python-poetry.org/

## Installation
- Run `poetry install` from the root directory. Then `poetry shell` to activate a virtual environment.
- Update `prod.env` with the right database url.
- Run `alembic upgrade head` to run the database migrations and create appropriate tables in your postgres db.
- Move to the src folder, and do `python __main__.py` to get the server up and running.
- Visit http://localhost:8101 to see the server in action. `/docs` for the documentation and `/graphql` for graphiql playground

## Things that I needed to do to get it all working
### Sqlalchemy and alembic
- Check `src/api/db/session.py` to see how we're creating the AsyncSession.
- We have to create a fastapi dependency so that we get a different db session every request. This dependency can be used in regular REST routes as well as the graphql route. Check `src/dependencies/db.py` to see the dependency.
- Our models are defined in `src/api/db/models` folder. All tables have to inherit from the Base class. Moreover, all these models have to be imported to a single file so that `Base.metadata` contains all the defined tables. We do that in the `__init__.py` in `src/api/db/models`.
- This repo already has alembic initialised, but when starting from scratch, run `alembic init src/api/db/models` to initiatlise alembic. This will create an `alembic.ini` file in the directory you are running it from, a `migrations` folder in the models folder. You'll have to edit `alembic.ini` and update `prepend_sys_path` to `./src` and `script_location` to `src/api/db/migrations`. Moreover alembic by default doesn't support async migrations. So you'll have to edit `src/api/db/migrations/env.py`. Check alembic documentation [here](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic). In the `env.py` file, you'll also have to set `target_metadata` to `Base.metadata`. This `Base` has to be imported from `api/db/models/__init__.py` and not `api/db/models/base.py`. In the env.py file, also set the database url by running `config.set_main_option("sqlalchemy.url", settings.database_dsn)`.
- To create alembic migrations, run `alembic revision --autogenerate -m "some message"`. To actually run the migrations, run `alembic upgrade head`. The repo already has the initial migrations checked in, so you can run upgrade command directly.
- For an example of how to use the session dependency we created, check `src/api/routers/resource.py` where we have a sample route which gets the session object using the dependency. This session will be closed after the request is done.
- Strawberry's graphql route can take a context generator as input. A dict has to be returned from this context generator, and the context is updated with this dict. You can find this context generator in `src/api/graphql/core/context.py`, and this context generator is used in `src/api/app.py`. Now in your graphql resolvers and queries, you can do `info.context['db']` to get the async session.

### Relay
There's a basic example in strawberry documentation about how to leverage python's generic types to create the required `Connection`, `Node` and `Edge` types. It works perfectly and you can check the documentation [here](https://strawberry.rocks/docs/guides/pagination). However, I wasn't exactly clear on where to go from there. How do we do cursor based pagination when we want to sort on columns other than the primary key column?

This kind of pagination is called keyset pagination. There's this library [sqlakeyset](https://github.com/djrobstep/sqlakeyset) which does keyset pagination for sqlalchemy. Unfortunatley, it doesn't have async support. But, there's a fork that does support it, and it can be found [here](https://github.com/Apakottur/sqlakeyset). There's no python pacakge for this repo, and I had to make a few changes to get it working for me, so I just copied over the entire thing and put it in `src/aio_sqlakeyset` folder. All the credit goes to the authors of that fork.

So this is how it works. To the `get_page` method of `aio_sqlakeyset` you give as input a query, a session to run your query on, a place - basically a bookmark. It is a tuple of column values. Let us say you want rows after id 10, name 50, the place would be (10, 50) - and other pagination info like how many rows do you want and whether you should move forward of backwards. Keep in mind that your query has to include atleast one `order_by` expression, and incase you are sorting based on a non-unique column, include another `order_by` expression with unique primary key so that you don't miss any rows. Your query must include all filters and order bys, but no limits. The `paginate` method takes care of doing the pagination part.

So, that's keyset pagination in the bag. Now we have to link it to graphql. You can read relay connection spec online, but in short these are the following requirements.
- You have to return a connection type. This type has `pageInfo` type, and `edges` type. `pageInfo` has `has_next_page`, `has_previous_page`, `start_cursor` and `end_cursor`. `start_cursor` and `end_cursor` are the cursors corresponding to the first and last element in your returned values, and they help with backward and forward pagination respectively.
- Each `edge` type must have a `node` (which is the actualy type that the client wants) and any additional metadata that is valid in context of this connection. A common metadata to return is a `cursor`. This cursor (and the start and end cursors) are valid only in context of this pagination. For example, if you're sorting based on `name` you will get a cursor that is completely different from the cursor you get while sorting based on `id` or any other field.
- Each node has and `id` field which is globally unique. Unlike the cursors, this ID will be same for a given node. This ID is calculated from the node type and the node id, so it is not dependent on what pagination params you provide.
- So what exactly are the pagination params? There are four of those: `first`, `last`, `before` and `after`. First and last are integers, and before and after are string cursors. `first` and `after` together are used for forward pagination (`first:10, after: <cursor>` means give me 10 elements after the given cursor), and `last` and `before` are used for backward pagination.

The utils needed to translate `aio_sqlakeyset` to our relay style params, there's a `PaginationHelper` class written in `src/api/graphql/core/relay.py`. This class takes care of validating the pagination params (We support only forward/backward pagination not both in the same request, `first` and `last` must be non negative integers etc). The code in `PaginationHelper` is pretty straight forward, so you can go through it. Here's how you'd use it:
```python
# create a helper object
helper = PaginationHelper(first=10, after="<cursor>", before=None, last=None)
# create a query with atleast one order by
query = select(ResourceModel.id).order_by(ResourceModel.id) # we'll add sorters based on input a bit later
# paginate results
_data = helper.paginate(query)
# _data has "nodes" a list of objects returned by your query, and "paging" an object containing information about first, last cursors and has_next and has_previous
return helper.build_connection(**_data)
```
and voila we are done. You might have noticed that we are not using dataloaders in the above code, but dataloaders are a recommended way of fetching data in graphql applications. So, what gives? Go to `On the subject of dataloaders` for explanation on that, because there's still another thing to do to get the `relay` style of things working.

Cool, we've got pagination. Next is globally unique ID fields for each type. In relay, each type must define an `id` field which returns a unique id. This unique id is calculated using the type name and the id of the entity. You can import `to_global_id` from `graphql_relay` to construct such an ID. But it is cumbersome to define that field and peform that translation on every type. To simplify that process you can use an extension that automatically converts all `id` fields of type `strawberry.ID` into such global IDs. The extension (`RelayIdExtension`) for that can be found in `src/api/graphql/core/extensions.py`. (Credit goes to @andrewingram on discord who has kindly provided this extension).

### On the subject of dataloaders
Dataloaders in graphql are used to solve the `N+1` problem (you can read about it online). Basically they batch requests together (`SELECT table.id FROM table WHERE table.id IN (1, 2, ...)` instead of `SELECT table.id FROM table WHERE table.id = 1; SELECT table.id FROM table WHERE table.id = 2; ...`), and cache responses at per request level. So if we have alread retrieved an object with id `1`, dataloader won't make another db call.

So all good right? Dataloaders are amazing in simple cases where you can easily batch requests together. But the query to batch requests get more and more and more complicated once you start adding filters and sorters. The query to batch requests with a lot of filters becomes so complicated so fast, that it is not worth to batch them together because you'll lose out on readability (and complex queries will introduce a lot of bugs). So I approach this problem in two ways.
- Use dataloader just for batching. you can do something like `return [await load_ele(**filters) for filter in filters]` in your dataloader. This won't batch your requests technically but it does cache them. So if in the same request another call to get resource is made with same filter, the dataloader can return from the cache.
- Split your query into two separate query. In the first query, just fetch `id`s of your resource, and then use a simple ID based dataloader to fetch the actual resources. The `id` query will be fast since it is returning minimal data, and the ID based dataloader can batch all ids together and fetch them in a single query. Sure, this is not completely optimal, but a completely optimal solution is very hard to get and requires a lot of expertise in writing SQL queries which most of us don't have.

In this demo, the second approach is used while paginating the results. You can find example of this in `src/api/graphql/resource/schema.py` and `src/api/graphql/tag/schema.py`.

Also, though strawberry has its own dataloader, I chose to use `aiodataloader` as it seemed more flexible and had more features.

There's another thing you have to remember about dataloaders. The dataloader cache/batching is at instance level. So if you create a two different dataloaders in the same request to fetch the same resource, you will get no benefit of caching or batching. It is commonly recommended to instantiate all your dataloaders and insert them into your context at the start of yoru request, and all your resolvers can get the dataloaders from this context and use them. Since the context expires after a request, it makes perfect sense to store them in context. The idea is sound, but the execution is a bit iffy. I don't like importing all my dataloaders (in large projects, you might have hundreds of dataloaders) in one file and putting them in context and making resolvers use string keys to get the dataloaders from context. So, I went with a different approach.

Basically, whenever a new object of a dataloader is created, we first check if an object with the specified key has already been stored in context. If yes, we return from context, otherwise we create a new dataloader, put it in context, and then return it. Each resolver directly instantiates a dataloader, and our dataloader takes care of returning the already instantiated instance. To accomplish this, we create a new base dataloader which inherits from `aiodataloader` and override its `__new__` method. The code for it can be found in `src/api/graphql/core/dataloader.py`. So, whenever you create a new dataloader, make sure it inherits from our base dataloader, and defines a `context_key` class variable. `context[context_key]` will have instance corresponding to that dataloader.

So, single instance of a dataloader at request level is solved. What next? There's another small gotcha you have to be aware of. When you want to load multiple things in parallel from dataloader, you do `dataloader(context).load_many(**keys)`. It is equivalent to doing `asyncio.gather(dataloader(context).load(key1), datalaoder(context).load(key2), ...)`. You will notice that that results you get back may not be in the same order as the keys you sent in. `Asyncio.gather` method starts execution in the order of inputs. But some executions may finish earlier than others, so the returned values are usually not in the same order as your inputs. When we are doing sorting, the order is important. So our base dataloader has an overwritten `load_many` method that ensures order if an `order_key` is found in the dataloader. The code is found in `src/api/graphql/core/dataloader.py` and examples of dataloaders can be found in `src/api/graphql/resource/dataloaders.py` and `src/api/graphql/tag/dataloader.py`.

### Sorters and filters
One last thing. How do we do sorting and filtering in a way that keeps the code relatively clean and not make our resolvers super bloated? My solution for that is to have the `sorter` and `filter` input objects to take care of the sorting. Each query which needs sorting/filtering, needs to accept two inputs. `sortBy` and `filter`. These are strawberry input objects. Each sorter must inherit from `BaseSorter` and each filter must inherit from `BaseFilter`. `BaseSorter` and `BaseFilter` can be found in `src/api/graphql/core/types.py`. They enforce that each sorter must define an `_add_sorters()` method which takes as input a sqlalchemy query (like `select(ResourceModel)`), and applies all the required sorters on that query. Similarly, each filter must define an add `_add_filters()` method which takes an sqlalchemy query input, and applies all the required filters on that query. Each sorter and filter can additionally define a `validate()` method which is called before adding filters or sorters.

This way, in your resolver all you have to do is `query = sortBy.add_sorters(filter.add_filters(base_query))` without having to worry about how exactly these sorters/filters are being applied. Example of such sorters and filters can be found in `src/api/graphql/resource/types.py` and `src/api/graphql/tag/types.py`. I have deliberately chosen a little bit involved example. Our datamodel involves many-to-many relationship between A `Resource` and a `Tag`, and searching based on tags is a very common usecase. The `ResourcesFilter` shows how to add filters for such a usecase, alongside other filters. You can also perform more complicated actions like `joins` etc inside your `_add_filters` or `_add_sorters` methods.

A final example of a query which has both relay style pagination and filters/sorters on it would be something like this:
```python
    @strawberry.field
    async def resources(
        self,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        sortBy: ResourcesSorter = ResourcesSorter.default(),
        filter: ResourcesFilter = ResourcesFilter.default(),
    ) -> Connection[Resource]:
        """
        We fetch paginated ids first and then use dataloader to fetch resources
        associated with those ids to leverage dataloader cache.
        """
        db = info.context["db"]
        helper = PaginationHelper(before, after, first, last)
        query = sortBy.add_sorters(filter.add_filters(select(ResourceModel.id)))
        _data = await helper.paginate(query=query, db=db)
        _data["nodes"] = await ResourceByIdLoader(info.context).load_many(
            _node[0] for _node in _data["nodes"]
        ) # _node[0] because _node is of form (id,).
        return helper.build_connection(**_data)
```

### Query Cost Validator
To protect your server from malicious actors, graphql servers usually have validators like query depth validator (which limits depth of incoming queries) and query cost/complexity validator (which limits the cost of incoming queries). Strawberry already has a depth limit validator extension (`from strawberry.extensions import QueryDepthLimiter`), but no complexity validator. Fortunately, `ariadne`, another graphql library, does have a validation rule. And that validation rule works directly in strawberry if you use `AddValidationRules` extension which lets you add custom validation rules. So that's what this demo uses.

There's a small gotcha here. It is a common practice to use `@cost` directive to indicate the cost of resolving a particular query or a type or a field. But I could not get that working. Instead I went ahead with the `cost_map` approach, where you define cost configuration in one dictionary. This dictionary would look something like this:
```python
cost_map = {
    "Query": {
        "resources": {"complexity": 1, "multipliers": ["first", "last"]}
    }
}
```
I have made changes in the validation rule so that `first` and `last` are used as multipliers by default, and each field already has a default `complexity` of 1, so you only have to edit this `cost_map` f you want to override something. A default complexity is calculated even with an empty cost_map and this would be enough for majority of use cases. Please go through ariadne's documentation [here](https://ariadnegraphql.org/docs/query-validators) for detailed information.

## Conclusion
So that is it. When I first started on working on a project using fastapi, strawberry, sqlalchemy (async) with relay style pagination, clean way of handling dataloaders and sorters/filters, I had to get information from a lot of different sources and do a lot of research. So, I made this demo so that all the information is collected in one place. Hopefully the ideas here help someone out there and save a bit of time.

Huge thanks to the kind folks like @patrick.py and @andrewingram on strawberry discord who answered my questions and helped me out!


```

## License

MIT

**Free Software, Hell Yeah!**
