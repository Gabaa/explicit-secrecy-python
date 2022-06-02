"""
Unsafe: only list-wide taint is stored

expsec_public: a
"""

a = [1, 2, 3]
b = 4
a[0] = b
b = a[0]
print(b)
