# dockor stuck
PS C:\Users\Acer\Downloads\samanvaya\implementation3\openimis-be_py> type docker-compose.yml
version: "3.7"

services:
  db:
    container_name: ${PROJECT_NAME:-openimis}-db
    image: ghcr.io/openimis/openimis-pgsql:${DB_TAG:-develop}
    environment:
      - POSTGRES_PASSWORD=$PSQL_DB_PASSWORD
      - POSTGRES_DB=$PSQL_DB_NAME
      - POSTGRES_USER=$PSQL_DB_USER
    healthcheck:
      test: ['CMD', 'pg_isready', '-U', "$PSQL_DB_USER", '-d', "test_imis"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    volumes:
      - database:/var/lib/postgresql/data
    restart: always
    ports:
      - 5432:5432
  db-mssql:
    container_name: ${PROJECT_NAME:-openimis}-mssql
    image: ghcr.io/openimis/openimis-mssql:${DB_TAG:-develop}
    restart: always
    user: root
    environment:
      - DB_PASSWORD=$MSSQL_DB_PASSWORD
      - SA_PASSWORD=$MSSQL_DB_PASSWORD
      - DB_NAME=$MSSQL_DB_NAME
      - DB_USER=$MSSQL_DB_USER
      - ACCEPT_EULA=Y
      - INIT_MODE=demo
    healthcheck:
      test: "bash /app/healthcheck.sh"
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 100s
    volumes:
      - database-mssql:/var/opt/mssql/data
    ports:
      - 1433:1433
  opensearch:
    image: opensearchproject/opensearch:latest
    env_file:
      - ".env.openSearch"
    environment:
      - "discovery.type=single-node"
      - "cluster.name=${CLUSTER_NAME:-my_opensearch_local}"
      - "http.port=${OPEN_SEARCH_HTTP_PORT:-9200}"
      - "plugins.security.ssl.http.enabled=${SLL_HTTP_ENABLED:-false}"
      - "plugins.security.disabled=true"
      - "OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}"
    volumes:
      - "opensearch-data:/usr/share/opensearch/data"

volumes:
  database:
  database-mssql:
  opensearch-data:


# status 2
PS C:\Users\Acer\Downloads\samanvaya\implementation3\openimis-be_py> type .env
>> 
# Database PSQL
PSQL_DB_USER=IMISuser
PSQL_DB_PASSWORD=IMISuser@1234
PSQL_DB_PORT=5432
PSQL_DB_ENGINE=django.db.backends.postgresql
PSQL_DB_HOST=127.0.0.1
PSQL_DB_NAME=test_imis
# Database MSSQL
MSSQL_DB_PORT=1433
MSSQL_DB_ENGINE=mssql
MSSQL_DB_USER=SA
MSSQL_DB_PASSWORD=IMISuser@1234
MSSQL_DB_NAME=test_imis
MSSQL_DB_HOST=127.0.0.1

DB_NAME=test_imis
DB_TEST_NAME=test_imis

# Site root that will prefix all exposed endpoints. It's required when working with openIMIS frontend
SITE_ROOT=api
# Should the debug be on (i.e. debug information will be displayed)
MODE=DEV
# this will also show the DB request in the console
DJANGO_DB_LOG_HANDLER=console
# Photo path root used in insuree module. Only used if InsureeConfig value not specified. Comment out for default.
#PHOTO_ROOT_PATH=<photo path>
# Should the database be migrated before start (entrypoint.sh - docker setup). Will be migrated anyway if $SITE_ROOT=api. Comment out for False
DJANGO_MIGRATE=True

PROJECT_NAME=dev
# set up you main domain
#DOMAIN=dev-openimis.org
HTTP_PORT=80
HTTPS_PORT=443
DB_DEFAULT=postgresql
# Comment  if you don't want to initialize with the demo dataset
DEMO_DATASET=true

DB_BRANCH=develop
GW_BRANCH=develop
BE_BRANCH=develop
FE_BRANCH=develop

# Lockout mechanism
# Allowed login failures before lockout
LOGIN_LOCKOUT_FAILURE_LIMIT=5
# Lockout duration in minutes
LOGIN_LOCKOUT_COOLOFF_TIME=5 

PASSWORD_MIN_LENGTH=8
# Minimum number of uppercase letters
PASSWORD_UPPERCASE=1
# Minimum number of lowercase letters
PASSWORD_LOWERCASE=1 
# Minimum number of digits
PASSWORD_DIGITS=1
# Minimum number of symbols
PASSWORD_SYMBOLS=1 
# Maximum number of spaces allowed
PASSWORD_SPACES=1 

# Define the trusted origins for CSRF protection, separated by commas
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:8000 

# Rate limiting settings
# The cache alias to use for rate limiting
RATELIMIT_CACHE=default  
# Key to identify the client; 'ip' means it will use the client's IP address
RATELIMIT_KEY=ip  
# Rate limit (150 requests per minute)
RATELIMIT_RATE=150/m  
# HTTP methods to rate limit; 'ALL' means all methods
RATELIMIT_METHOD=ALL  
# Group name for the rate limit
RATELIMIT_GROUP=graphql 
# Whether to skip rate limiting
RATELIMIT_SKIP_TIMEOUT=False

OPENSEARCH_ADMIN=admin
OPENSEARCH_PASSWORD=B9wc9VrqX7pY