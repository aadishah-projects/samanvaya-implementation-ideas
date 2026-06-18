"""
URL configuration — includes Samanvaya webhook endpoint + GraphQL.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    # GraphQL endpoint — csrf_exempt for GraphiQL/testing (real OpenIMIS uses JWT auth)
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # Samanvaya webhook (receives callbacks from Mock Bank)
    path("", include("samanvaya.urls")),
]
"""
URL configuration — includes Samanvaya webhook endpoint + GraphQL.
"""
from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    # GraphQL endpoint (OpenIMIS uses this for all API calls)
    path("graphql/", GraphQLView.as_view(graphiql=True)),
    # Samanvaya webhook (receives callbacks from Mock Bank)
    path("", include("samanvaya.urls")),
]
