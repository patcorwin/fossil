''' Allow temporary memoization with in a context so batched actions can run faseter.


ex:
```

mult = 3

@session_memoize
def global_mod(x):
    global mult
    return x * mult


print(global_mod(3)) # 3 * 3 = 9

with session():
    print( global_mod(4) ) # 12
    
    mult = 5

    print( global_mod(4) ) # still 12 due to session


print( global_mod(4) ) # 20 since we're out of the session

```

'''

from contextlib import contextmanager


_session_memoize_stack = 0
_session_memoize_cache = {}


@contextmanager
def session():
    global _session_memoize_stack
    global _session_memoize_cache

    _session_memoize_stack += 1

    try:
        yield
    except Exception:
        raise
    finally:
        _session_memoize_stack -= 1
        if not _session_memoize_stack:
            _session_memoize_cache = {}


def session_memoize(func):

    def wrapped(*args, **kwargs):
        global _session_memoize_stack
        global _session_memoize_cache

        if _session_memoize_stack:
            temp = _session_memoize_cache.setdefault(func, {})
            
            if args not in temp:
                temp[args] = func(*args, **kwargs)
            
            return temp[args]
        else:
            return func(*args, **kwargs)

    return wrapped
