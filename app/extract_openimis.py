import psycopg2
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

try:
    from .config import OPENIMIS_URL, JWT_TOKEN, DB_CONFIG
except ImportError:
    from config import OPENIMIS_URL, JWT_TOKEN, DB_CONFIG

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
    print(f"Extracting claims from OpenIMIS GraphQL API ({OPENIMIS_URL})...")
    try:
        result = client.execute(QUERY)
    except Exception as e:
        print(f"Failed to connect to OpenIMIS: {e}")
        return

    claims = result['claims']['edges']
    print(f"Fetched {len(claims)} claims. Loading to Postgres...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("ALTER TABLE staging_openimis_claims ADD COLUMN IF NOT EXISTS district TEXT;")
    cur.execute("TRUNCATE TABLE staging_openimis_claims;")

    for edge in claims:
        node = edge['node']
        cur.execute("""
            INSERT INTO staging_openimis_claims (uuid, code, date_claimed, amount_claimed, hospital_name, district, status_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            node['uuid'],
            node['code'],
            node['dateClaimed'],
            float(node['claimed']),
            node['healthFacility']['name'] if node['healthFacility'] else 'Unknown',
            'Unknown',
            node['status']
        ))

    conn.commit()
    cur.close()
    conn.close()
    print("OpenIMIS data successfully loaded into staging table!")

if __name__ == "__main__":
    extract_and_load()
