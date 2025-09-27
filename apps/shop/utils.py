from drf_yasg.utils import swagger_auto_schema
from api.pagination import PAGINATION_PARAMS


# def swagger_helper(tags, model): # Moved to api/utils.py
#     def decorators(func):
#         descriptions = {
#             "list": f"Retrieve a list of {model}",
#             "retrieve": f"Retrieve details of a specific {model}",
#             "create": f"Create a new {model}",
#             "partial_update": f"Update a {model}",
#             "destroy": f"Delete a {model}",
#         }

#         action_type = func.__name__
#         get_description = descriptions.get(action_type, f"{action_type} {model}")
#         return swagger_auto_schema(manual_parameters=PAGINATION_PARAMS, operation_id=f"{action_type} {model}", operation_description=get_description, tags=[tags])(func)

#     return decorators