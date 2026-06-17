import psycopg2
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

OPENIMIS_URL = "http://localhost:8001/api/graphql"
JWT_TOKEN = "mock_openimis_jwt_secret_12345"

transport = RequestsHTTPTransport(
    url=OPENIMIS_URL,
    headers={"Authorization": f"JWT {JWT_TOKEN}"},
    verify=True,
    retries=3,
)
client = Client(transport=transport, fetch_schema_from_transport=False)

QUERY = gql("""
    query GetApprovedClaims {
        claims(status: 4, first: 100) {
            edges {
                node {
                    uuid
                    code
                    dateClaimed
                    claimed
                    status
                    healthFacility {
                        name
                    }
                }
            }
        }
    }
""")

def extract_and_load():
    print("Extracting claims from OpenIMIS GraphQL API...")
    try:
        result = client.execute(QUERY)
    except Exception as e:
        print(f"Failed to connect to OpenIMIS: {e}")
        return

    claims = result['claims']['edges']
    print(f"Fetched {len(claims)} claims. Loading to Postgres...")

    conn = psycopg2.connect(
        dbname="samanvaya",
        user="postgres",
        password="secret",
        host="localhost",
        port=5433
    )
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE staging_openimis_claims;")

    for edge in claims:
        node = edge['node']
        cur.execute("""
            INSERT INTO staging_openimis_claims (uuid, code, date_claimed, amount_claimed, hospital_name, status_code)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            node['uuid'],
            node['code'],
            node['dateClaimed'],
            float(node['claimed']),
            node['healthFacility']['name'] if node['healthFacility'] else 'Unknown',
            node['status']
        ))

    conn.commit()
    cur.close()
    conn.close()
    print("OpenIMIS data successfully loaded into staging table!")

if __name__ == "__main__":
    extract_and_load()
