ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 144, in __init__
    self._dbapi_connection = engine.raw_connection()
                             ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 3319, in raw_connection
    return self.pool.connect()
           ^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 448, in connect
    return _ConnectionFairy._checkout(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 1272, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 712, in checkout
    rec = pool._do_get()
          ^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\impl.py", line 178, in _do_get
    with util.safe_reraise():
  File "C:\New folder\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 122, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\impl.py", line 176, in _do_get
    return self._create_connection()
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 389, in _create_connection
    return _ConnectionRecord(self)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 674, in __init__
    self.__connect()
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 900, in __connect
    with util.safe_reraise():
  File "C:\New folder\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 122, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 896, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\create.py", line 667, in connect
    return dialect.connect(*cargs_tup, **cparams)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\default.py", line 630, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\psycopg2\__init__.py", line 135, in connect
    conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: FATAL:  password authentication failed for user "postgres"


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\New folder\Lib\site-packages\uvicorn\protocols\http\h11_impl.py", line 403, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\applications.py", line 113, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\New folder\Lib\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\New folder\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\New folder\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\New folder\Lib\site-packages\starlette\routing.py", line 715, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\routing.py", line 735, in app
    await route.handle(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\New folder\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\New folder\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\New folder\Lib\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\fastapi\routing.py", line 301, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\fastapi\routing.py", line 214, in run_endpoint_function
    return await run_in_threadpool(dependant.call, **values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\starlette\concurrency.py", line 39, in run_in_threadpool
    return await anyio.to_thread.run_sync(func, *args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\anyio\to_thread.py", line 56, in run_sync
    return await get_async_backend().run_sync_in_worker_thread(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\anyio\_backends\_asyncio.py", line 2461, in run_sync_in_worker_thread
    return await future
           ^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\anyio\_backends\_asyncio.py", line 962, in run
    result = context.run(func, *args)
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Acer\Downloads\samanvaya\basic_implementation\main.py", line 50, in get_reconciliation
    return {"data": run_reconciliation()}
                    ^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Acer\Downloads\samanvaya\basic_implementation\main.py", line 14, in run_reconciliation
    claims = pd.read_sql("SELECT * FROM openimis_claims", engine)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\pandas\io\sql.py", line 700, in read_sql
    with pandasSQL_builder(con) as pandas_sql:
         ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\pandas\io\sql.py", line 908, in pandasSQL_builder
    return SQLDatabase(con, schema, need_transaction)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\pandas\io\sql.py", line 1649, in __init__
    con = self.exit_stack.enter_context(con.connect())
                                        ^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 3295, in connect
    return self._connection_cls(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 146, in __init__
    Connection._handle_dbapi_exception_noconnection(
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 2450, in _handle_dbapi_exception_noconnection
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 144, in __init__
    self._dbapi_connection = engine.raw_connection()
                             ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\base.py", line 3319, in raw_connection
    return self.pool.connect()
           ^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 448, in connect
    return _ConnectionFairy._checkout(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 1272, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 712, in checkout
    rec = pool._do_get()
          ^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\impl.py", line 178, in _do_get
    with util.safe_reraise():
  File "C:\New folder\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 122, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\impl.py", line 176, in _do_get
    return self._create_connection()
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 389, in _create_connection
    return _ConnectionRecord(self)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 674, in __init__
    self.__connect()
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 900, in __connect
    with util.safe_reraise():
  File "C:\New folder\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 122, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\New folder\Lib\site-packages\sqlalchemy\pool\base.py", line 896, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\create.py", line 667, in connect
    return dialect.connect(*cargs_tup, **cparams)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\sqlalchemy\engine\default.py", line 630, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\New folder\Lib\site-packages\psycopg2\__init__.py", line 135, in connect
    conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "localhost" (::1), port 5432 failed: FATAL:  password authentication failed for user "postgres"

(Background on this error at: https://sqlalche.me/e/20/e3q8)







