# claim_extraction/constants.py

PYTHON_BUILTINS = {
    'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'print', 'range', 'enumerate', 'map', 'filter', 'sum', 'min', 'max',
    'any', 'all', 'isinstance', 'hasattr', 'getattr', 'setattr', 'super',
    'open', 'type', 'repr', 'sorted', 'reversed', 'zip', 'iter', 'next',
    'abs', 'round', 'ord', 'chr', 'hex', 'bin', 'oct', 'format', 'id',
    'input', 'hash', 'callable', 'dir', 'vars', 'locals', 'globals',
    'upper', 'lower', 'strip', 'lstrip', 'rstrip', 'split', 'rsplit',
    'join', 'replace', 'startswith', 'endswith', 'find', 'rfind',
    'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'copy',
    'keys', 'values', 'items', 'get', 'update', 'setdefault',
    'read', 'write', 'close', 'seek', 'tell', 'flush',
}

PYTHON_KEYWORDS = {
    'if', 'else', 'elif', 'for', 'while', 'with', 'try', 'except', 'finally',
    'return', 'yield', 'raise', 'import', 'from', 'as', 'pass', 'break',
    'continue', 'lambda', 'assert', 'global', 'nonlocal', 'class', 'def',
    'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None', 'async', 'await',
}

OBSERVABLE_KEYWORDS = {
    'return', 'returns', 'raise', 'raises', 'exception', 'error',
    'equal', 'equals', 'output', 'result', 'value', 'state',
    'attribute', 'property', 'contain', 'contains', 'produce',
    'must be', 'should be', 'will be', 'not raise', 'not throw',
    'is none', 'is not none', 'true', 'false', 'empty', 'list', 'dict'
}

ELIGIBILITY_EXCEPTION_KEYWORDS = {
    'ValueError', 'TypeError', 'KeyError', 'AttributeError', 'IndexError',
    'RuntimeError', 'ImportError', 'IOError', 'OSError', 'FileNotFoundError',
    'AssertionError', 'NotImplementedError', 'StopIteration', 'Exception'
}

ELIGIBILITY_BEHAVIOR_KEYWORDS = {
    'should return', 'should raise', 'must return', 'must raise',
    'returns', 'raises', 'incorrectly', 'fails to', 'does not',
    'expected', 'unexpected', 'wrong', 'incorrect', 'invalid'
}
