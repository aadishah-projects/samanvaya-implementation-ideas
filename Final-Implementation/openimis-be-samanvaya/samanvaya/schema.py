"""
Root GraphQL schema aggregator for the Samanvaya module.
OpenIMIS discovers module schemas via: schema.schema.Query and schema.schema.Mutation
"""
import graphene
from .gql_queries import Query as SamanvayaQuery
from .gql_mutations import Mutation as SamanvayaMutation


class Query(SamanvayaQuery, graphene.ObjectType):
    pass


class Mutation(SamanvayaMutation, graphene.ObjectType):
    pass


# OpenIMIS convention: schema.schema.Query / schema.schema.Mutation
schema = graphene.Schema(query=Query, mutation=Mutation)

# Also export for standalone test harness compatibility
schema_query = Query
schema_mutation = Mutation
"""
Root GraphQL schema aggregator for the Samanvaya module.
OpenIMIS discovers module schemas through this file.
"""
from .gql_queries import Query
from .gql_mutations import Mutation

# OpenIMIS uses these to merge module schemas into the root schema
schema_query = Query
schema_mutation = Mutation
