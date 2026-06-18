"""
Root GraphQL schema — aggregates OpenIMIS core + Samanvaya schemas.
"""
import graphene
from samanvaya.gql_queries import Query as SamanvayaQuery
from samanvaya.gql_mutations import Mutation as SamanvayaMutation


class Query(SamanvayaQuery, graphene.ObjectType):
    pass


class Mutation(SamanvayaMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
