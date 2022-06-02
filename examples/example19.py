"""
Unsafe: a preserves its tainted status

expsec_public: a
"""

a = [1, 2, 3]   # `a` is untainted
b = [4, 5, 6]   # `b` is tainted
a = b           # now `a` is tainted
a = [7, 8, 9]   # should `a` be tainted now?
print(a)
