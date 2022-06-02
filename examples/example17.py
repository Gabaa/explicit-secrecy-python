"""
Unsafe: a and b are aliases

expsec_public: a, b
"""

a = [1, 2, 3]
b = a
c = 10
b[0] = c
print(a)
