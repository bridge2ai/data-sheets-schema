"""Typed adapter shutdown evidence; settled charges alone are not closure."""
from budgeted_cborg import BudgetStop


def require_closed(runtime, style):
    if not isinstance(runtime, dict):
        raise BudgetStop('evaluation lacks actual adapter closure evidence')
    if style in {'semantic_agent', 'field_agent'}:
        closed = (runtime.get('adapter') == 'native' and type(runtime.get('exit_code')) is int
            and runtime['exit_code'] == 0
            and runtime.get('proxy_initialized') is True
            and runtime.get('proxy_shutdown_complete') is True
            and type(runtime.get('unfinished_handlers')) is int
            and runtime['unfinished_handlers'] == 0)
    else:
        cleanup = runtime.get('client_cleanup', {})
        closed = (runtime.get('adapter') == 'api'
            and runtime.get('complete_response') is True
            and runtime.get('request_lifetime_frozen') is True
            and type(runtime.get('independent_requests')) is int and runtime['independent_requests'] == 1
            and isinstance(cleanup, dict) and cleanup.get('owned') is True
            and cleanup.get('completed') is True and 'error_type' not in cleanup)
    if not closed:
        raise BudgetStop('evaluation adapter did not close all request and client activity')
    return runtime
