Diagnosing whether the container’s TCP auth settings or stored password differ from the expected `secret`.

Ran terminal command: cd 'C:\Users\Acer\Downloads\samanvaya\implementation2' ; docker exec samanvaya-db sh -lc 'printf "--- pg_hba.conf ---\n"; sed -n "1,40p" /var/lib/postgresql/data/pg_hba.conf; printf "\n--- tcp test ---\n"; PGPASSWORD=secret psql -h 127.0.0.1 -U postgres -d samanvaya -c "\dt"'
Completed with input: cd 'C:\Users\Acer\Downloads\samanvaya\implementation2' ; docker exec samanvaya-db sh -lc 'printf "--- pg_hba.conf ---\n"; sed -n "1,40p" /var/lib/postgresql/data/pg_hba.conf; printf "\n--- tcp test ---\n"; PGPASSWORD=secret psql -h 127.0.0.1 -U postgres -d samanvaya -c "\dt"'

I'm verifying the container's internal authentication config and whether `postgres/secret` works over TCP.

Ran terminal command: cd 'C:\Users\Acer\Downloads\samanvaya\implementation2' ; docker exec samanvaya-db sh -c 'echo "--- pg_hba.conf ---"; sed -n "1,80p" /var/lib/postgresql/data/pg_hba.conf; echo "--- tcp test ---"; PGPASSWORD=secret psql -h 127.0.0.1 -U postgres -d samanvaya -c "\dt"'

Checking the container's internal auth settings and testing TCP login directly from the container.

Ran terminal command: cd 'C:\Users\Acer\Downloads\samanvaya\implementation2' ; docker exec samanvaya-db sh -c 'echo "--- pg_hba.conf ---"; sed -n "1,80p" /var/lib/postgresql/data/pg_hba.conf; echo "--- tcp test secret ---"; PGPASSWORD=secret psql -h 127.0.0.1 -U postgres -d samanvaya -c "\dt"'

Verifying whether Windows itself is answering localhost:5432 instead of the Docker container.

Ran terminal command: cd 'C:\Users\Acer\Downloads\samanvaya\implementation2' ; docker port samanvaya-db 5432 ; echo ====== ; netstat -ano | findstr ":5432" ; echo ====== ; Test-NetConnection -ComputerName localhost -Port 5432

Checking which Windows processes own port 5432 so I can tell you whether the container is being masked by a local Postgres service.

Ran terminal command: Get-Process -Id 3500,7692 | Format-Table Id,ProcessName,Path -AutoSize

I’m identifying the Windows Postgres service that is conflicting with Docker so I can give you the cleanest fix.

Ran terminal command: Get-CimInstance Win32_Service | Where-Object {$_.ProcessId -eq 7692} | Select-Object Name,DisplayName,State,StartMode,ProcessId | Format-List

Identifying the Windows process behind PID 7692 so I can tell you whether a local Postgres installation is causing the conflict.

Ran terminal command: Get-CimInstance Win32_Process -Filter "ProcessId=7692" | Select-Object ProcessId,Name,CommandLine | Format-List

Now I’m checking whether the Windows `postgres.exe` is managed by a service you can stop cleanly.

Ran terminal command: Get-Service | Where-Object {$_.Name -like '*postgres*' -or $_.DisplayName -like '*postgres*'} | Select-Object Name,DisplayName,Status,StartType | Format-Table -AutoSize

Completed: *Start or restart Docker Desktop if needed* (2/6)

Great — the issue is now clear.

## Root cause

- Docker container `samanvaya-db` is listening on port `5432`.
- Windows also has a local Postgres service `postgresql-x64-18` listening on port `5432`.
- Your Python script is connecting to `localhost:5432`, and Windows is answering first with the local Postgres instance.
- That local service rejects `postgres/secret`, so the failure is exactly this conflict.

## What to do

### Option 1: Use the Docker container on a different host port
Stop and restart the Docker container mapped to a free port, e.g. `5433`:

```powershell
docker stop samanvaya-db
docker rm samanvaya-db
docker run --name samanvaya-db -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=samanvaya -p 5433:5432 -d postgres:15
```

Then run:

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "5433"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "secret"
python .\seed_data.py
```

### Option 2: Stop the local Windows Postgres service
If you want `localhost:5432` to refer to Docker, stop the Windows Postgres service:

```powershell
Stop-Service -Name postgresql-x64-18
```

Then run your script again with `DB_PORT=5432`.

> If you stop the Windows Postgres service, verify with:
> `netstat -ano | findstr ":5432"`

## Recommended fix

I recommend Option 1 because it avoids changing your Windows Postgres installation and keeps the two databases separate.

If you want, I can also update seed_data.py to use a default `DB_PORT=5433` for this repo, with a comment explaining the Docker port mapping.